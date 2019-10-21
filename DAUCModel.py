# -*- coding: utf-8 -*-

"""
Created on Sun Feb 10 11:06:17 2019

@author: SMU Team (J. Wang, Z. Li, S. Yin)

Copyright preserved by the author. No distribution is allowed unless authorized by the author.
"""

# Using DAT as Input to Creat pyomo.AbstractModel()
# ============= What we considered here ==========================
# 1. The initial status (Hour0, Status0, Power0) in the minon/minoff constraints
# 2. The asymmetic regulation up and dow capacity in the PFR and AGC parts with different system 
#    requrements and prices, but there is NO PFR for Regulation down service!!!
# 3. Generators are assumed to run with four-block piece-wise linear generation cost curves
# 4. SUcost/SDCost/No_load_cost are considered
# 5. Line flow is modelled through PTDF
# ============= What we assumed here =============================
# 1. The cost curve of a generator is convex
# 2. Network losses are negligible
# 3. ACG is in the  direction of PFR, so pos.(neg.) PFR is followed by pos.(neg.) AGC
# ================================================================

import pyomo.environ as pe


# =================== Modelling ==================================
UCmdl = pe.AbstractModel(name="Dayahead_UC")

# ------------------$ Parameter Section $-------------------------
# Define Index Sets
UCmdl.HOUR_SET     = pe.Set() # Store the id of every time period
UCmdl.GEN_SET      = pe.Set() # Store the id of every generator
UCmdl.LOAD_BUS_SET = pe.Set() # Store the id of every load/bus
UCmdl.LINE_SET     = pe.Set() # Store the id of every line

# Param. for Frequency and Dynamic Input
# ! Param in this part are the very ones that interact with DynSim. !
UCmdl.F0       = pe.Param() # Unit: Hz, Nominal frequency f0
UCmdl.Df_Max   = pe.Param() # Unit: Hz, Maximum frequency deviation
UCmdl.Rec_Time = pe.Param() # Unit: min. Time required to recover to nominal frequency
UCmdl.Pfr_Pen  = pe.Param() # Penalty for insufficient PFR reserve
UCmdl.Agc_Pen  = pe.Param() # Penalty for insufficient AGC reserve
UCmdl.Pfr_Pos_Req = pe.Param(UCmdl.HOUR_SET) # Requirement for PFR reserve
UCmdl.Pfr_Neg_Req = pe.Param(UCmdl.HOUR_SET) # Requirement for PFR reserve
UCmdl.Agc_Pos_Req = pe.Param(UCmdl.HOUR_SET) # Requirement for AGC reserve
UCmdl.Agc_Neg_Req = pe.Param(UCmdl.HOUR_SET) # Requirement for AGC reserve
# Param for Generation
UCmdl.Gen_Bus = pe.Param(UCmdl.GEN_SET) # Location Bus
UCmdl.Gen_Max = pe.Param(UCmdl.GEN_SET, UCmdl.HOUR_SET) # Upper Bound
UCmdl.Gen_Min = pe.Param(UCmdl.GEN_SET) # Lower Bound
UCmdl.Gen_K1  = pe.Param(UCmdl.GEN_SET) # Linear Gen. Price for BLK1
UCmdl.Gen_SP1 = pe.Param(UCmdl.GEN_SET) # Span for BLK 1
UCmdl.Gen_K2  = pe.Param(UCmdl.GEN_SET) # Linear Gen. Price for BLK2
UCmdl.Gen_SP2 = pe.Param(UCmdl.GEN_SET) # Threshold for BLK 2
UCmdl.Gen_K3  = pe.Param(UCmdl.GEN_SET) # Linear Gen. Price for BLK1
UCmdl.Gen_SP3 = pe.Param(UCmdl.GEN_SET) # Span for BLK 1
UCmdl.Gen_K4  = pe.Param(UCmdl.GEN_SET) # Linear Gen. Price for BLK2
UCmdl.Gen_SP4 = pe.Param(UCmdl.GEN_SET) # Threshold for BLK 2
# Param for UC
UCmdl.Gen_Hour0  = pe.Param(UCmdl.GEN_SET) # Initial Hours that Gen. Runs for
UCmdl.Gen_Stat0  = pe.Param(UCmdl.GEN_SET) # Initial Status
UCmdl.Gen_Pow0   = pe.Param(UCmdl.GEN_SET) # Initial Power
UCmdl.Gen_Minon  = pe.Param(UCmdl.GEN_SET) # MinOn time
UCmdl.Gen_Minoff = pe.Param(UCmdl.GEN_SET) # MinOff time
UCmdl.Gen_SUcost = pe.Param(UCmdl.GEN_SET) # Startup cost
UCmdl.Gen_SDcost = pe.Param(UCmdl.GEN_SET) # Shutdown cost
UCmdl.Gen_NLcost = pe.Param(UCmdl.GEN_SET) # Noload cost
# Param. for PFR/AGC
UCmdl.Gen_DB = pe.Param(UCmdl.GEN_SET) # Governor Dead Band (Hz)
UCmdl.Gen_Ri = pe.Param(UCmdl.GEN_SET) # Equivalent Droop Constant
UCmdl.Gen_RR = pe.Param(UCmdl.GEN_SET) # Ramp Rate (MW/min)
UCmdl.PFR_UP_Prc = pe.Param(UCmdl.GEN_SET) # Linear PFR UP Cap. Price
UCmdl.PFR_DN_Prc = pe.Param(UCmdl.GEN_SET) # Linear PFR DN Cap. Price
UCmdl.AGC_UP_Prc = pe.Param(UCmdl.GEN_SET) # Linear AGC UP Cap. Price
UCmdl.AGC_DN_Prc = pe.Param(UCmdl.GEN_SET) # Linear AGC DN Cap. Price
# Param for Load
UCmdl.Load_All = pe.Param(UCmdl.HOUR_SET) # System Load
UCmdl.Load_Bus = pe.Param(UCmdl.LOAD_BUS_SET, UCmdl.HOUR_SET) # Bus Load
UCmdl.Load_Damp_Cof = pe.Param(UCmdl.HOUR_SET) # System Load Damp Coefficient
UCmdl.Researve_All  = pe.Param(UCmdl.HOUR_SET) # System Researve
# Param for Line
UCmdl.Ln_Cap  = pe.Param(UCmdl.LINE_SET) # Line Power Cap.
UCmdl.Ln_PTDF = pe.Param(UCmdl.LINE_SET, UCmdl.LOAD_BUS_SET) # PTDF

# ------------------$ Generator Model Section $-----------------------
# Declare the variable Power of Generators and Constraints
UCmdl.gen_onoff   = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, domain = pe.Binary)
UCmdl.gen_startup = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, domain = pe.Binary)
UCmdl.gen_shutdow = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, domain = pe.Binary)
UCmdl.gen_power   = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, domain = pe.NonNegativeReals)

# Constraints
# -- Generation Capacity (Hourly changeable)
def gen_cap_upper_rule(UCmdl, gi, hi):
    return UCmdl.gen_power[gi,hi] <= UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Max[gi,hi]
UCmdl.gen_cap_upper = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_cap_upper_rule)

def gen_cap_lower_rule(UCmdl, gi, hi):
    return UCmdl.gen_power[gi,hi] >= UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Min[gi]
UCmdl.gen_cap_lower = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_cap_lower_rule)

# -- Power and Block-variables for every generators
def gen_block1_rule(UCmdl, gi, hi):
    return (0, UCmdl.Gen_SP1[gi])
UCmdl.gen_blk1 = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = gen_block1_rule)

def gen_block2_rule(UCmdl, gi, hi):
    return (0, UCmdl.Gen_SP2[gi])
UCmdl.gen_blk2 = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = gen_block2_rule)

def gen_block3_rule(UCmdl, gi, hi):
    return (0, UCmdl.Gen_SP3[gi])
UCmdl.gen_blk3 = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = gen_block3_rule)

def gen_block4_rule(UCmdl, gi, hi):
    return (0, UCmdl.Gen_SP4[gi])
UCmdl.gen_blk4 = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = gen_block4_rule)

def gen_pow_and_blks_rule(UCmdl, gi, hi): # We assume that the cost function is convex!
    return UCmdl.gen_power[gi,hi] == UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Min[gi]\
                                   + UCmdl.gen_blk1[gi,hi] + UCmdl.gen_blk2[gi,hi]\
                                   + UCmdl.gen_blk3[gi,hi] + UCmdl.gen_blk4[gi,hi]
UCmdl.gen_pow_and_blks = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_pow_and_blks_rule)

# -- Ramp Rate
def gen_ramp_up_rule(UCmdl, gi, hi):
    if hi < 2:
        return UCmdl.gen_power[gi,hi] - UCmdl.Gen_Pow0[gi] <= UCmdl.Gen_RR[gi] * 60
    else:
        return UCmdl.gen_power[gi,hi] - UCmdl.gen_power[gi,hi-1] <= UCmdl.Gen_RR[gi] * 60
UCmdl.gen_ramp_up = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_ramp_up_rule)

def gen_ramp_down_rule(UCmdl, gi, hi):
    if hi < 2:
        return UCmdl.gen_power[gi,hi] - UCmdl.Gen_Pow0[gi] >= -UCmdl.Gen_RR[gi] * 60
    else:
        return UCmdl.gen_power[gi,hi] - UCmdl.gen_power[gi,hi-1] >= -UCmdl.Gen_RR[gi] * 60
UCmdl.gen_ramp_down = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_ramp_down_rule)

# -- Logic constraints for gen. binary variables
def gen_start_shut_onoff_rule(UCmdl, gi, hi):
    if hi < 2: # Init Status
        return UCmdl.gen_startup[gi,hi] - UCmdl.gen_shutdow[gi,hi] \
               == UCmdl.gen_onoff[gi,hi] - UCmdl.Gen_Stat0[gi]
    else:
        return UCmdl.gen_startup[gi,hi] - UCmdl.gen_shutdow[gi,hi] \
               == UCmdl.gen_onoff[gi,hi] - UCmdl.gen_onoff[gi,hi-1]
UCmdl.gen_start_shut_onoff = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_start_shut_onoff_rule)

def gen_no_meantime_up_down_rule(UCmdl, gi, hi):
    return UCmdl.gen_startup[gi,hi] + UCmdl.gen_shutdow[gi,hi] <= 1.0001
UCmdl.gen_no_meantime_up_down = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_no_meantime_up_down_rule)

# -- MinOn and MinOff Times
def gen_minon_rule(UCmdl, gi, hi):
    TimeSpan = len(UCmdl.HOUR_SET)
    if UCmdl.Gen_Minon[gi] < 1: # No need to consider the minon
        return pe.Constraint.Skip
    # Otherwise, the following codes are to consider the minon constraints:
    if UCmdl.Gen_Stat0[gi] == 1 and UCmdl.Gen_Minon[gi] > UCmdl.Gen_Hour0[gi]:
        if hi < UCmdl.Gen_Minon[gi]-UCmdl.Gen_Hour0[gi]: # determine the remaining hours
            return UCmdl.gen_onoff[gi,hi] == 1 # it should be on for these hours
        #The following hours have satisfied the initial conditions:
        elif hi > TimeSpan - UCmdl.Gen_Minon[gi] + 1: # If the hour approches the end of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_startup[gi,hi]
        else: # for the hours in the middle of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minon[gi])) ) >= UCmdl.Gen_Minon[gi] * UCmdl.gen_startup[gi,hi]
    elif UCmdl.Gen_Stat0[gi] == 1 and UCmdl.Gen_Minon[gi] <= UCmdl.Gen_Hour0[gi]:
        # Hence the initial conditions have been satisfied, simply run:
        if hi > TimeSpan - UCmdl.Gen_Minon[gi] + 1: # If the hour approches the end of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_startup[gi,hi]
        else: # for the hours in the middle of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minon[gi])) ) >= UCmdl.Gen_Minon[gi] * UCmdl.gen_startup[gi,hi]
    elif UCmdl.Gen_Stat0[gi] == 0 and UCmdl.Gen_Minoff[gi] <= UCmdl.Gen_Hour0[gi]:
         # Hence the initial conditions have been satisfied, simply run:
        if hi > TimeSpan - UCmdl.Gen_Minon[gi] + 1: # If the hour approches the end of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_startup[gi,hi]
        else: # for the hours in the middle of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minon[gi])) ) >= UCmdl.Gen_Minon[gi] * UCmdl.gen_startup[gi,hi]
    elif UCmdl.Gen_Stat0[gi] == 0 and UCmdl.Gen_Minoff[gi] > UCmdl.Gen_Hour0[gi]:
        if hi < UCmdl.Gen_Minoff[gi]-UCmdl.Gen_Hour0[gi]: # determine the remaining hours
            return UCmdl.gen_onoff[gi,hi] == 0 # it should be off for these hours
         #The following hours have satisfied the initial conditions:
        elif hi > TimeSpan - UCmdl.Gen_Minon[gi] + 1: # If the hour approches the end of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_startup[gi,hi]
        else: # for the hours in the middle of the day
            return sum(UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minon[gi])) ) >= UCmdl.Gen_Minon[gi] * UCmdl.gen_startup[gi,hi]
UCmdl.gen_minon = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_minon_rule)

def gen_minoff_rule(UCmdl, gi, hi):
    TimeSpan = len(UCmdl.HOUR_SET)
    if UCmdl.Gen_Minoff[gi] < 1: # No need to consider the minon
        return pe.Constraint.Skip
    # Otherwise, the following codes are to consider the minon constraints:
    if UCmdl.Gen_Stat0[gi] == 1 and UCmdl.Gen_Minon[gi] > UCmdl.Gen_Hour0[gi]:
        if hi < UCmdl.Gen_Minon[gi]-UCmdl.Gen_Hour0[gi]:
            return pe.Constraint.Skip # Because UCmdl.gen_onoff[gi,hi] == 1 has been considered in UCmdl.gen_minon
        elif hi > TimeSpan - UCmdl.Gen_Minoff[gi] + 1: # If the hour approches the end of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_shutdow[gi,hi]
        else: # for the hours in the middle of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minoff[gi])) ) >= UCmdl.Gen_Minoff[gi] * UCmdl.gen_shutdow[gi,hi]
    elif UCmdl.Gen_Stat0[gi] == 1 and UCmdl.Gen_Minon[gi] <= UCmdl.Gen_Hour0[gi]:
        # Hence the initial conditions have been satisfied, simply run:
        if hi > TimeSpan - UCmdl.Gen_Minoff[gi] + 1: # If the hour approches the end of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_shutdow[gi,hi]
        else: # for the hours in the middle of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minoff[gi])) ) >= UCmdl.Gen_Minoff[gi] * UCmdl.gen_shutdow[gi,hi]
    elif UCmdl.Gen_Stat0[gi] == 0 and UCmdl.Gen_Minoff[gi] <= UCmdl.Gen_Hour0[gi]:
        # Hence the initial conditions have been satisfied, simply run:
        if hi > TimeSpan - UCmdl.Gen_Minoff[gi] + 1: # If the hour approches the end of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_shutdow[gi,hi]
        else: # for the hours in the middle of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minoff[gi])) ) >= UCmdl.Gen_Minoff[gi] * UCmdl.gen_shutdow[gi,hi]
    elif UCmdl.Gen_Stat0[gi] == 0 and UCmdl.Gen_Minoff[gi] > UCmdl.Gen_Hour0[gi]:
        if hi < UCmdl.Gen_Minoff[gi]-UCmdl.Gen_Hour0[gi]: # determine the remaining hours
            return pe.Constraint.Skip # Because UCmdl.gen_onoff[gi,hi] == 0 has been considered in UCmdl.gen_minon
         #The following hours have satisfied the initial conditions:
        elif hi > TimeSpan - UCmdl.Gen_Minoff[gi] + 1: # If the hour approches the end of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi,TimeSpan+1)) >= (TimeSpan - hi + 1) * UCmdl.gen_shutdow[gi,hi]
        else: # for the hours in the middle of the day
            return sum(1-UCmdl.gen_onoff[gi,ti] for ti in range(hi, hi+int(UCmdl.Gen_Minoff[gi])) ) >= UCmdl.Gen_Minoff[gi] * UCmdl.gen_shutdow[gi,hi]
UCmdl.gen_minoff = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_minoff_rule)

# -- Pos. PFR of each generator 
def pfr_pos_cap_rule(UCmdl, gi, hi): # deltaf_max = 0.2 Hz, DB = 0.036 Hz
    return (0, (UCmdl.Df_Max - UCmdl.Gen_DB[gi]) / UCmdl.Gen_Ri[gi])
UCmdl.gen_pfr_pos = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = pfr_pos_cap_rule)

def gen_pow_add_pfr_rule(UCmdl, gi, hi):
    return UCmdl.gen_power[gi,hi] + UCmdl.gen_pfr_pos[gi,hi] <= UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Max[gi,hi]
UCmdl.gen_pow_add_pf = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_pow_add_pfr_rule)

# -- Neg. PFR of each generator 
def pfr_neg_cap_rule(UCmdl, gi, hi): # deltaf_max = 0.2 Hz, DB = 0.036 Hz
    return (0, 0*(UCmdl.Df_Max - UCmdl.Gen_DB[gi]) / UCmdl.Gen_Ri[gi])
UCmdl.gen_pfr_neg = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = pfr_neg_cap_rule)

def gen_pow_sub_pfr_rule(UCmdl, gi, hi):
    return UCmdl.gen_power[gi,hi] - UCmdl.gen_pfr_neg[gi,hi] >= UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Min[gi]
UCmdl.gen_pow_sub_pfr = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_pow_sub_pfr_rule)

# -- Pos. AGC of each generator
def agc_pos_cap_rule(UCmdl, gi, hi):
    return (0, UCmdl.Gen_RR[gi] * UCmdl.Rec_Time)
UCmdl.gen_agc_pos = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = agc_pos_cap_rule)

## We assume that ACG is in the  direction of PFR
def gen_pow_add_pfr_agc_rule(UCmdl, gi, hi):
    return UCmdl.gen_power[gi,hi] + UCmdl.gen_pfr_pos[gi,hi] + UCmdl.gen_agc_pos[gi,hi] <= UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Max[gi,hi]
UCmdl.gen_pow_add_pfr_agc = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_pow_add_pfr_agc_rule)

# -- Neg. AGC of each generator
def agc_neg_cap_rule(UCmdl, gi, hi):
    return (0, UCmdl.Gen_RR[gi] * UCmdl.Rec_Time)
UCmdl.gen_agc_neg = pe.Var(UCmdl.GEN_SET, UCmdl.HOUR_SET, bounds = agc_neg_cap_rule)

## We assume that ACG is in the  direction of PFR
def gen_pow_sub_pfr_agc_rule(UCmdl, gi, hi):
    return UCmdl.gen_power[gi,hi] - UCmdl.gen_pfr_neg[gi,hi] - UCmdl.gen_agc_neg[gi,hi] >= UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Min[gi]
UCmdl.gen_pow_sub_pfr_agc = pe.Constraint(UCmdl.GEN_SET, UCmdl.HOUR_SET, rule = gen_pow_sub_pfr_agc_rule)
# ---------------------$ End Section $--------------------------

# ------------------$ Line Flow Section $-----------------------
def ln_frflow_cap_rule(UCmdl, li, hi):
    return sum(UCmdl.Ln_PTDF[li,UCmdl.Gen_Bus[gi]] * UCmdl.gen_power[gi, hi] for gi in UCmdl.GEN_SET)\
         - sum(UCmdl.Ln_PTDF[li,ldi] * UCmdl.Load_Bus[ldi, hi] for ldi in UCmdl.LOAD_BUS_SET) <= UCmdl.Ln_Cap[li]
UCmdl.ln_frflow_cap = pe.Constraint(UCmdl.LINE_SET, UCmdl.HOUR_SET, rule = ln_frflow_cap_rule)

def ln_reflow_cap_rule(UCmdl, li, hi):
    return sum(UCmdl.Ln_PTDF[li,UCmdl.Gen_Bus[gi]] * UCmdl.gen_power[gi, hi] for gi in UCmdl.GEN_SET)\
         - sum(UCmdl.Ln_PTDF[li,ldi] * UCmdl.Load_Bus[ldi, hi] for ldi in UCmdl.LOAD_BUS_SET) >= -UCmdl.Ln_Cap[li]
UCmdl.ln_reflow_cap = pe.Constraint(UCmdl.LINE_SET, UCmdl.HOUR_SET, rule = ln_reflow_cap_rule)
# ---------------------$ End Section $--------------------------

# ----------------$ System Constraint Section $-------------------
# -- Load Balance 
def sys_load_bal_rule(UCmdl, hi):
    return sum(UCmdl.gen_power[gi, hi] for gi in UCmdl.GEN_SET) == UCmdl.Load_All[hi]
UCmdl.sys_load_balance = pe.Constraint(UCmdl.HOUR_SET, rule = sys_load_bal_rule)

# -- Researve Requirement
def sys_reserve_req_rule(UCmdl, hi):
    return sum(UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_Max[gi,hi] for gi in UCmdl.GEN_SET) >= UCmdl.Load_All[hi] + UCmdl.Researve_All[hi]
UCmdl.sys_reserve_req = pe.Constraint(UCmdl.HOUR_SET, rule = sys_reserve_req_rule)

# -- Pos. and Neg. PFR Requirements
# Pos. and Neg. PFR shortage
UCmdl.sys_IR1_pos = pe.Var(UCmdl.HOUR_SET, domain = pe.NonNegativeReals) # insuffient pos. PFR
UCmdl.sys_IR1_neg = pe.Var(UCmdl.HOUR_SET, domain = pe.NonNegativeReals) # insuffient neg. PFR

## System Pos. PFR requirement
def sys_pfr_pos_req_rule(UCmdl, hi):
    return sum(UCmdl.gen_pfr_pos[gi,hi] for gi in UCmdl.GEN_SET) \
           >= UCmdl.Pfr_Pos_Req[hi] - UCmdl.sys_IR1_pos[hi] \
              - UCmdl.Load_All[hi] * UCmdl.Load_Damp_Cof[hi] * UCmdl.Df_Max / UCmdl.F0
UCmdl.sys_pfr_pos_req = pe.Constraint(UCmdl.HOUR_SET, rule = sys_pfr_pos_req_rule)

## System Neg. PFR requirement
def sys_pfr_neg_req_rule(UCmdl, hi):
    return sum(UCmdl.gen_pfr_neg[gi,hi] for gi in UCmdl.GEN_SET) \
           >= UCmdl.Pfr_Neg_Req[hi] - UCmdl.sys_IR1_neg[hi] \
           - UCmdl.Load_All[hi] * UCmdl.Load_Damp_Cof[hi] * UCmdl.Df_Max / UCmdl.F0
UCmdl.sys_pfr_neg_req = pe.Constraint(UCmdl.HOUR_SET, rule = sys_pfr_neg_req_rule)

# -- Pos. and Neg. AGC Requirements
## Pos. and Neg. AGC shortage
UCmdl.sys_IR2_pos = pe.Var(UCmdl.HOUR_SET, domain = pe.NonNegativeReals) # insuffient pos. AGC
UCmdl.sys_IR2_neg = pe.Var(UCmdl.HOUR_SET, domain = pe.NonNegativeReals) # insuffient neg. AGC

## System Pos. AGC requirement
def sys_agc_pos_req_rule(UCmdl, hi):
    return sum(UCmdl.gen_agc_pos[gi,hi] for gi in UCmdl.GEN_SET) >= UCmdl.Agc_Pos_Req[hi] - UCmdl.sys_IR2_pos[hi]
UCmdl.sys_agc_pos_req = pe.Constraint(UCmdl.HOUR_SET, rule = sys_agc_pos_req_rule)

## System Neg. AGC requirement
def sys_agc_neg_req_rule(UCmdl, hi):
    return sum(UCmdl.gen_agc_neg[gi,hi] for gi in UCmdl.GEN_SET) >= UCmdl.Agc_Neg_Req[hi] - UCmdl.sys_IR2_neg[hi]
UCmdl.sys_agc_neg_req = pe.Constraint(UCmdl.HOUR_SET, rule = sys_agc_neg_req_rule)
# ---------------------$ End Section $--------------------------

# --------------------$ Objective Function $-----------------------------
def obj(UCmdl):
    # assume the cost of insufficient amount is 30
    return sum(UCmdl.gen_startup[gi,hi] * UCmdl.Gen_SUcost[gi]\
            + UCmdl.gen_shutdow[gi,hi] * UCmdl.Gen_SDcost[gi]\
            + UCmdl.gen_onoff[gi,hi] * UCmdl.Gen_NLcost[gi]\
            + UCmdl.gen_blk1[gi,hi] * UCmdl.Gen_K1[gi]\
            + UCmdl.gen_blk2[gi,hi] * UCmdl.Gen_K2[gi]\
            + UCmdl.gen_blk3[gi,hi] * UCmdl.Gen_K3[gi]\
            + UCmdl.gen_blk4[gi,hi] * UCmdl.Gen_K4[gi]\
            + UCmdl.gen_pfr_pos[gi,hi] * UCmdl.PFR_UP_Prc[gi]\
            + UCmdl.gen_pfr_neg[gi,hi] * UCmdl.PFR_DN_Prc[gi]\
            + UCmdl.gen_agc_pos[gi,hi] * UCmdl.AGC_UP_Prc[gi]\
            + UCmdl.gen_agc_neg[gi,hi] * UCmdl.AGC_DN_Prc[gi]\
              for gi in UCmdl.GEN_SET for hi in UCmdl.HOUR_SET)\
         + sum(UCmdl.Pfr_Pen * UCmdl.sys_IR1_pos[hi] + UCmdl.Pfr_Pen *UCmdl.sys_IR1_neg[hi]\
             + UCmdl.Agc_Pen * UCmdl.sys_IR2_pos[hi] + UCmdl.Agc_Pen *UCmdl.sys_IR2_neg[hi]\
               for hi in UCmdl.HOUR_SET)
UCmdl.OBJ = pe.Objective(rule = obj, sense = pe.minimize)
# ---------------------$ End Section $--------------------------
# ==================== End of Modelling =============================