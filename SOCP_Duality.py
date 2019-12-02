
# coding: utf-8

# In[1]:


import gurobipy as gp
import numpy as np
import pandas as pd


# In[2]:


## Primal Problem Statement

primal = gp.Model("SOCP_Primal")

# Add Coefficients

P_objcoe = [2, 1, 1, -3]

P_INEQ_RHS1 = 7
P_INEQ_COE1 = [1, 0, 0, 0]

P_EQ_RHS = 4
P_EQ_COE = [2, -1, 1, 0.5]

P_INEQ_RHS2 = 15
P_INEQ_COE2 = [1, 1, 0, -2]

# Add Variables
x = {}

for i in range(2):
    x[i] = primal.addVar(name = 'x('+str(i)+')', lb = 0, ub = gp.GRB.INFINITY)
    
for i in range(2,4):
    x[i] = primal.addVar(name = 'x('+str(i)+')', lb = -gp.GRB.INFINITY, ub = gp.GRB.INFINITY)
    
# Set Objective

primal.setObjective(sum(P_objcoe[i] * x[i] for i in range(4)), gp.GRB.MINIMIZE)

# Add Constraints

primal.addConstr(sum(P_INEQ_COE1[i] * x[i] for i in range(4)) <= P_INEQ_RHS1, 'INEQ1')
                 
primal.addConstr(sum(P_INEQ_COE2[i] * x[i] for i in range(4)) <= P_INEQ_RHS2, 'INEQ2')
                 
primal.addConstr(sum(P_EQ_COE[i] * x[i] for i in range(4)) == P_EQ_RHS, 'EQ')
                 
primal.addConstr(2 * x[0] * x[1] >= x[2] * x[2] + x[3] * x[3], 'CONE')

primal.update()

primal.setParam(gp.GRB.Param.Threads, 8)
primal.optimize()


# In[2]:


## Primal Problem Statement

dual = gp.Model("SOCP_Dual")

# Add Coefficients

Q_objcoe_Y = [-7, 4, -15]
Q_objcoe_Z = [0, 0, 0, 0]

Q_INEQ_RHS1 = -2
Q_INEQ_COE1_Y = [1, -2, 1]
Q_INEQ_COE1_Z = [-1, 0, 0, 0]

Q_INEQ_RHS2 = -1
Q_INEQ_COE2_Y = [0, 1, 1]
Q_INEQ_COE2_Z = [0, -1, 0, 0]

Q_EQ_RHS1 = -1
Q_EQ_COE1_Y = [0, -1, 0]
Q_EQ_COE1_Z = [0, 0, -1, 0]

Q_EQ_RHS2 = 3
Q_EQ_COE2_Y = [0, -0.5, -2]
Q_EQ_COE2_Z = [0, 0, 0, -1]

# Add Variables
y = {}
z = {}

for i in range(3):
    y[i] = dual.addVar(name = 'y('+str(i)+')', lb = -gp.GRB.INFINITY, ub = gp.GRB.INFINITY)
    if i == 0 or i == 2:
        y[i] = dual.addVar(name = 'y('+str(i)+')', lb = 0, ub = gp.GRB.INFINITY)
    
for i in range(4):
    z[i] = dual.addVar(name = 'z('+str(i)+')', lb = 0, ub = gp.GRB.INFINITY)
    if i >= 2:
        z[i] = dual.addVar(name = 'z('+str(i)+')', lb = -gp.GRB.INFINITY, ub = gp.GRB.INFINITY)
    
# Set Objective

dual.setObjective(sum(Q_objcoe_Y[i] * y[i] for i in range(3)) + sum(Q_objcoe_Z[i] * z[i] for i in range(4)), gp.GRB.MAXIMIZE)

# Add Constraints

dual.addConstr(sum(Q_INEQ_COE1_Y[i] * y[i] for i in range(3)) + sum(Q_INEQ_COE1_Z[i] * z[i] for i in range(4)) >= Q_INEQ_RHS1, 'INEQ1')
                 
dual.addConstr(sum(Q_INEQ_COE2_Y[i] * y[i] for i in range(3)) + sum(Q_INEQ_COE2_Z[i] * z[i] for i in range(4)) >= Q_INEQ_RHS2, 'INEQ2')

dual.addConstr(sum(Q_EQ_COE1_Y[i] * y[i] for i in range(3)) + sum(Q_EQ_COE1_Z[i] * z[i] for i in range(4)) == Q_EQ_RHS1, 'EQ1')

dual.addConstr(sum(Q_EQ_COE2_Y[i] * y[i] for i in range(3)) + sum(Q_EQ_COE2_Z[i] * z[i] for i in range(4)) == Q_EQ_RHS2, 'EQ2')
                 
dual.addConstr(2 * z[0] * z[1] >= z[2] * z[2] + z[3] * z[3], 'CONE')

dual.update()

dual.setParam(gp.GRB.Param.Threads, 8)
dual.optimize()


# In[3]:


dual.write("file.lp")

