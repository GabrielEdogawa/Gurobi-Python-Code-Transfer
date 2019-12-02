\ Model SOCP_Dual
\ LP format - for model browsing. Use MPS format to capture full model detail.
Maximize
  - 7 y(0) + 4 y(1) - 15 y(2)
Subject To
 INEQ1: y(0) - 2 y(1) + y(2) - z(0) >= -2
 INEQ2: y(1) + y(2) - z(1) >= -1
 EQ1: - y(1) - z(2) = -1
 EQ2: - 0.5 y(1) - 2 y(2) - z(3) = 3
 CONE: [ 2 z(0) * z(1) - z(2) ^2 - z(3) ^2 ] >= 0
Bounds
 y(0) free
 y(1) free
 y(2) free
 z(2) free
 z(3) free
End
