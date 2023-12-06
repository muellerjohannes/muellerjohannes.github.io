
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

### Geometry of Partially Observable Markov Decision Processes

* what is a POMDP?
* What is a state-action distribution?
* Linear programming formulation of MDPs
* polynomial programming formulation of POMDPs
* Crying baby example 

### Geometry of Natural Policy Gradient Methods

Natural policy gradient (NPG) methods are amongst the most successful reinforcement learning techniques and have received vastly growing attention from the theoretical reinforcement learning and control communities~\cite{?}.
Policy gradient methods in general aim to update the parameter $\theta$ of a stochastic policy $\pi_\theta\in\Delta_\mathcal A^\mathcal S$ to maximize the discounted reward 
First proposed by Sham M. Kakade, the parameter update of natural policy gradient methods takes the general form 

$$
    \theta_{k+1} = \theta_k + G(\theta_k)^+ \nabla R(\theta_k).
$$

Here $G(\theta)^+$ denotes an arbitrary pseudo-inverse of the Gramian matrix $G(\theta)$ with entries given by 
$G(\theta)_ {ij} = g_{d_\theta}(\partial_{\theta_i} d_\theta, \partial_{\theta_j} d_\theta)$, 
where $d_\theta\in\Delta_{\mathcal S\times\mathcal A}$ denotes the state-action distribution of the policy $\pi_\theta$ and $g$ is a Riemannian metric on the interior of the polytope of state-action distributions $D$. 

* complications of convergence analysis in the parameters and policies
* however, we can work with the underlying linear programmging formulation
* there, the corresponding state-acion distributions follow a Riemannian gradient flow with respect to the Hessian geometry induced by the conditional entropy
* this yields nice convergence results

**Theorem (Linear convergence of Kakade's NPG)**
*Let* $(d_t)_{t\ge0}$ *denote the solution of the natural policy gradient flow and assume that there is unique maximizer* $d^\star$ *of the reward. Then for all* $c_1\in(0, \Delta)$ *there is* $c_2>0$ *such that*

$$
    \sum_{s} \rho^\ast(s) D_{\text{KL}}(\pi^\ast(\cdot|s), \pi_t(\cdot|s)) \le c_2 e^{-c_1t}
$$

*and*

$$
    R^\ast - \mathfrak R(d_t) \le \frac{2c_2\lvert\mathcal S\rvert\lvert\mathcal A\rvert \cdot \lVert r \rVert_\infty}{(1-\gamma)\min_{s}   \rho^\ast(s)} \cdot e^{-c_1t},
$$

where 

$$
 \Delta = \min \left\\{ \frac{R^\ast -  \mathfrak R(d)}{\lVert d^\ast - d \rVert_{\text{TV}}} : d\in N(d^\ast) \right\\} = \min \left\\{ \frac{r^\top(d^\ast - d)}{\lVert d^\ast - d \rVert_{\text{TV}}} : d\in N(d^\ast) \right\\} > 0,
$$

and $N(d^\ast)$ denotes the neighboring vertices of $d^\ast$ in the state-action polytope $\mathcal D$. 


* Plateaus:
* Designing plateau free methods: 

### Energy Natural Gradients for Physics Informed Neural Networks

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
L(\theta) \coloneqq \int_\Omega (\Delta u_\theta + f)^2 \mathrm dx + \lambda\int_{\partial\Omega} (u-g)^2 \mathrm ds.
$$

Now, one employs some optimization procedure to minimize $L$ as $L(\theta) = 0$ ensures that $u_\theta$ solves the PDE. 
In fact, one can show that $\lVert u_\theta - u^\ast\rVert_{H^{1/2}(\Omega)} \le c \sqrt{L(\theta)}$ and if $u_\theta = g$ on $\partial\Omega$ then even $\lVert u_\theta - u^\ast\rVert_{H^{2}(\Omega)} \le c \sqrt{L(\theta)}$, where $u^\ast$ denotes the solution of the Poisson equation, see~[M. and Zeinhofer](https://proceedings.mlr.press/v190/muller22b.html). 
This ensures that successful optimization of $L$ implies approximation of the solution of the PDE. 

However, the biggest pitfall of PINNs is that they are known for being hard to optimize and common techniques for neural network training like (stochastic) gradient descent and Adam are well documented to saturate and fail to produce good approximations. 
The current consensus is that amongst the traditional iterative solvers applied to $L$ the quasi-Newton L-BFGS yields the best results. 
However, it still fails to achieve the best approximation possible with the given network at hand. 

$$
G(\theta)_{ij} \coloneqq \int _\Omega \Delta \partial _{\theta_i} u _\theta \Delta \partial _{\theta_j} u _\theta \mathrm dx + \int _{\partial\Omega} \partial _{\theta_i} u _\theta \partial _{\theta_j} u _\theta \mathrm ds.
$$

asdfasdf

$$
\partial_t u_{\theta+tv} = \Pi_{T\mathcal F_{\Theta}}(u^\ast-u_\theta)
$$

asdfasdf

$$
u_{\theta+\Delta_tv} =  u_\theta + \Delta_t \cdot \Pi_{T_\theta\mathcal F_\Theta}(u^\ast-u_\theta) + O(\Delta_t^2)
$$

* Plots of push forwards
* Videos
* Plots showing that we obtain high accuracy
* Equivalence to GN in the residuals
* Future work: scaling things up; convergence theory










