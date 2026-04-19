# Architecture Note: Reverse Advection & The Effector-Calorimeter Loop   (just a thought)
**Module:** `pack_effector` (Parallel Development)
**Status:** Experimental / Draft Design
**Date:** April 2026

## 1. Abstract and Motivation
Standard MPC is purely epistemic: it models what a system can coherently believe given its history and a finite energy budget. However, to navigate an environment (e.g., a maze), the system must execute actions based on desired future states. 

This note outlines an experimental framework for the **Effector Module**, which links motor control and prediction error directly into the thermodynamic Calorimeter. It achieves this by introducing **Reverse Advection**—a physical mechanism that translates goal-directed predictions into geometric trails that pull the system forward, effectively bridging MPC with Active Inference.

## 2. The Ontological Boundary (Strict Separation)
To prevent conflating "what is true" (inference) with "what is useful" (control), the core MPC Substrate must remain strictly forward-time. The Reverse Advection mechanics exist **only within the Effector-Calorimeter loop**. 

* **The Core Brain:** Solves standard forward SDEs based on history ($d_A$).
* **The Effector Pack:** Projects anticipatory trails ($a_A$) and feeds the resulting geometric shear back into the Calorimeter as a measurement of *surprise*.

## 3. The Physics of Reverse Advection
In MSRJD field theory, the response field propagates backward in time. We instantiate this physically by giving the effector the ability to project an **Anticipatory Trail Vector**, $a_A(t)$.

* **History Trail ($d_A$):** Points from the crystallized past to the present. It provides advective momentum.
* **Anticipatory Trail ($a_A$):** Points from the predicted/desired future state backward to the present. It provides advective suction.

Within the Effector's local scope, the modified generalized Langevin drift becomes a bidirectional tension:
$$\dot{x}_{\text{motor}}(t) = \eta_{\text{past}} d_A(t) + \eta_{\text{future}} a_A(t) + \sum \chi_{AB} \, \text{proj}_{d_A}(a_A) + \sqrt{2D_{\text{eff}}} \xi$$

The agent's motor plan is now modeled as a particle suspended on a string between its memory ($d_A$) and its expectation ($a_A$).

## 4. The Thermodynamics of Surprise (Calorimeter Upgrades)
Because we have dropped the microscopic Landauer cost (bit erasure) as indistinguishable from noise, the Calorimeter's primary function in the Effector loop is to track **Trajectory Surprise**.

When we evaluate the tensorial FDT mechanics across both past and future trails, cross-dissipation ($\chi_{AB}$) takes on a new physical meaning: **Prediction Error.**

* **Alignment (Cooperative Drift):** If $d_A$ (memory says "go left") and $a_A$ (prediction says "go left") are parallel, the trails mutually reinforce. The effector executes smoothly with minimal heat loss.
* **Temporal Shear (Destructive Interference):** If reality forces $d_A$ to deviate from the predicted goal $a_A$, the geometric projection induces massive temporal shear ($\chi_{AB} > 0$). 

The Calorimeter registers this shear as a massive spike in **Conflict Heat**. The system is burning metabolic flux because its memories are physically colliding with its expectations. 
