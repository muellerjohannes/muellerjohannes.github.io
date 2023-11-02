---
layout: archive
title: "Research"
permalink: /research/
author_profile: true
---

My research interests lie at the intersection of machine learning and applied mathematics. In particular, this includes the following topics:
* Geometry of Markov decision processes
* Representational capacity of neural networks
* Connections between neural networks and differential equations

**Geometry of Partially Observable Markov Decision Processes**
Markov decision processes 

**Geometry of Natural Policy Gradient Methods**

**Energy Natural Gradients for Physics Informed Neural Networks**
Neural network-based PDE solvers receive quickly growing attention within the scientific machine learning and applied mathematics communities. 
One of the most popular approaches is the one of *Physics Informed Neural Networks (PINNs)* or *Deep Galerkin Method (DGM)* which relies on minimizing the residual of the PDE.
For example, for the Poisson equation 

$$ 
\begin{align} -\Delta u & = f \quad \text{in } \Omega \\ 
u & = g \quad\text{on } \partial\Omega 
\end{align} 
$$

with Dirichlet boundary condition on a smooth domain $\Omega\subseteq\mathbb R^d$.
The idea of PINNs and the DGM is to consider a function $u_\theta\colon\mathbb R^d\to\mathbb R$ computed by a neural network with parameters $\theta$ and to minimize the residual which leads to the following objective function 

$$
L(\theta) \coloneqq \frac12\int_\Omega (\Delta u_\theta + f)^2 \mathrm dx + \frac12\int_{\partial\Omega} (u-g) \mathrm ds.
$$
