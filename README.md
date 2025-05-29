# Satellite-based Quantum Key Distribution Scheduling Optimisation

This repository is part of a master's thesis in Computer Science at RWTH Aachen University. The thesis focuses on optimising the scheduling of communication in satellite-based Quantum Key Distribution (SatQKD) networks. It contains the implementation of data, solvers, and Sequential Model-based Algorithm Configuration (SMAC) using [Sparkle](https://github.com/ADA-research/Sparkle).

## 🛰️ Project Overview

Quantum Key Distribution enables secure communication using the principles of quantum mechanics. However, long-distance QKD requires satellite-based infrastructure. This project models a concrete scheduling problem for SatQKD networks and explores how solver technologies and automated algorithm configuration can be used to improve performance.

### Contributions and Analysis
- Modelling the SatQKD scheduling problem using:
  - Integer Linear Programming
  - Constraint satisfaction-based approaches
- Implementation of solvers:
  - Gurobi
  - SCIP
  - Timefold
- Application of algorithm configuration using:
  - SMAC
- Dataset generation based on satellite passes and secure key rate estimations for European ground stations
- Solver performance is evaluated using:
  - Solution quality
  - Runtime and PAR10 (Penalised Average Runtime with factor 10)

## 📄 Licence

This project is licensed under the [MIT Licence](./LICENSE).

## ✉️ Contact

For questions or collaborations, please contact:  
**Leon Kamke**  
Email: *leonkamke98@gmail.com*  
Degree: MSc in Computer Science
