
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
Markov decision processes 

### Geometry of Natural Policy Gradient Methods

Natural policy gradient (NPG) methods are amongst the most successful reinforcement learning techniques and have received vastly growing attention from the theoretical reinforcement learning and control communities~\cite{?}.
Policy gradient methods in general aim to update the parameter $\theta$ of a stochastic policy $\pi_\theta\in\Delta_\mathcal A^\mathcal S$ to maximize the discounted reward 
%\begin{equation}
    $R(\theta) = R(\pi_\theta)$. 
    %= (1-\gamma)\mathbb E\left[ \sum_{t\in\mathbb N} \gamma^t r(S_t, A_t)\right],
%\end{equation}
%where $\gamma\in[0, 1)$ denote the discount factor and $(S_t, A_t)_{t\in\mathbb N}$ denotes the Markov process obtained when following the policy $\pi_\theta$. 
%where $S_t$ and $A_t$ denote the (random) state and action at time $t$, where $S_0$ is distributed according to $\mu\in\Delta_\mathcal S$.
First proposed by Kakade~\cite{?}, the parameter update of natural policy gradient methods takes the general form 
\begin{equation}
    \theta_{k+1} = \theta_k + G(\theta_k)^+ \nabla R(\theta_k).
\end{equation}
Here $G(\theta_k)^+$ denotes an arbitrary pseudo-inverse of the Gramian matrix $G(\theta_k)$ with entries given by $G(\theta)_{ij} = g_{d_\theta}(\partial_{\theta_i} d_\theta, \partial_{\theta_j} d_\theta)$, where $d_\theta\in\Delta_{\mathcal S\times\mathcal A}$ denotes the state-action distribution of the policy $\pi_\theta$ and $g$ is a Riemannian metric on the interior of the polytope of state-action distributions $D$. 

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












