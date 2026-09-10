#import "@preview/cv-soft-and-hard:0.1.0": styling, section, entry, subsection, rust, cpp, python, typst-logo, hugo, typescript

#set document(author: "Johannes Christoph Müller", title: "CV Johannes Christoph Müller")
#show: styling

#align(center)[
  = Johannes Christoph Müller\
  	Institut für Mathematik, Technische Universität Berlin
    \ 
    Straße des 17. Juni 136, 
10623 Berlin\
  #link("https://muellerjohannes.github.io/", "muellerjohannes.github.io/") |
  // #link("https://www.github.com/", "github.com/jonaspleyer") |
  #link("mailto:johannes.christoph.mueller@tu-berlin.de", "johannes.christoph.mueller@tu-berlin.de") // |
  // #link("tel:+491785430064", "+49 178 5430064")
]

//Experience
#section("Experience")
#entry(
  [
    *Postdoctoral Researcher* (_Technische Universität Berlin_)
    in the research group _Stochastische Analysis_ led by _Prof. Dr. Benjamin Gess_
  ],
  [_since 03/2025_]
)
#entry(
  [
    *Scientific employee* (_RWTH Aachen University_)
    of the Junior Professorship on _Mathematical Foundations of Deep Learning_ held by _Prof. Dr. Semih Çaycı_
  ],
  [_09/2023--09/2024_]
)
#entry(
  [
    *PhD Student* (_Max-Planck Institute for Mathematics in the Sciences, Leipzig_)
  ],
  [_01/2020--08/2023_]
)

#section("Education")
#entry(
  [
    *Max-Planck-Institute for Mathematics in the Sciences & Leipzig University*\
    Dr. rer. nat. in Mathematics, _Summa cum laude_\
    // #text([Thesis: "_Agent-based Models in Cellular Systems_" (Christian Fleck)], size: 9pt)\
    // MSc. Physics (Theoretical Physics & Mathematics),\
    #text([Thesis: _Geometry of Optimization in Markov Decision Processes and Neural Network-Based PDE Solvers_, supervised by _Prof. Dr. Nihat Ay_ and _Prof. Dr. Guido Montúfar_], size: 9pt)
  ],
  [\
    _2020--2024_
  ],
)
#entry(
  [
    *University of Warwick* \ 
    MSc. in Interdisciplinary Mathematics, _Distinction_\
  ],
  [\
    _2017--2018_
  ],
)
#entry(
  [
    *Freiburg University* \ 
    MSc. Mathematics, Grade: 1.0\ 
    Bsc. Mathematics, Grade: 1.1\
  ],
  [\
    _2016--2019\
    2013--2016_
  ],
)

#section("Third-party funding")
#entry(
  [
    *PhD Scholarship*, Evangelisches Studienwerk Villigst e.V. (#sym.tilde\€50k)
  ],
  [_2021--2023_],
)
#entry(
  [
    *International Max Planck Research School* for Mathematics in the Sciences, MPI MiS
  ],
  [_2020--2023_],
)
#entry(
  [
    *SIAM Travel Award* (\$800)
  ],
  [_2022_],
)
#entry(
  [
    *Scholarship*, Evangelisches Studienwerk Villigst e.V. (#sym.tilde\€30k)
  ],
  [_2015--2019_],
)

#section("Teaching and supervision")
#subsection("Supervision")
#entry(
  [
    *Reza Zolnouri*, Master thesis in Mathematics\
    #text([_The Role of the Geometry in Policy Mirror Descent_], size: 9pt)
  ],
  [_2024_],
)
#entry(
  [
    *Jonas Nießen*, Master thesis in Mathematics\
    #text([_Optimization guarantees for Physics-Informed Neural Networks_], size: 9pt)
  ],
  [_2023/2024_],
)
#entry(
  [
    *Friedrich Wicke*, Undergraduate intern in Mathematics\
    #text([_State-Action Geometry of Multi-Agent Problems_], size: 9pt)
  ],
  [_2022_],
)

#subsection("Teaching assistant")
#entry([Seminar on _Neural Network Approximation Theory_], [_2024_])
#entry([_Mathematical Foundations of Deep Learning_], [_2023/2024_])

#subsection("Tutor")
#entry([Analysis I & II], [_2018--2019_])
#entry([Linear Algebra, Measure and Integration Theory, Functional Analysis], [_2015--2017_])

#section("Reviewing activities")
#subsection("Journals")
- Science Advances
- SIAM Journal on Mathematical Analysis
- IEEE Transactions on Automatic Control
- Transactions on Machine Learning Research
- Information Geometry
- Engineering Applications of Artificial Intelligence

#subsection("Conferences")
- International Conference on Machine Learning (ICML)
- International Conference on Learning Representations (ICLR)

#section("Talks and presentations")
#subsection("Talks")
#entry(
  [
    *Geometry and Convergence of Natural Policy Gradient Methods*\
    #text([Seminar on Learning Theory and Statistical Optimization, University of Oxford], size: 9pt)
  ],
  [_06/2024_],
)
#entry(
  [
    *Geometry of Optimization in Scientific Machine Learning and Reinforcement Learning*\
    #text([Invited talk, Geometric Deep Learning workshop, University of Cambridge], size: 9pt)
  ],
  [_06/2024_],
)
#entry(
  [
    *Achieving High Accuracy with PINNs via Energy Natural Gradient Descent*\
    #text([PhysicsX, London], size: 9pt)
  ],
  [_06/2024_],
)
#entry(
  [
    *Natural Gradients for Scientific Machine Learning*\
    #text([Post Graduate Seminar, Chair of Mathematics of Information Processing, RWTH Aachen], size: 9pt)
  ],
  [_01/2024_],
)
#entry(
  [
    *Theoretical Analysis of Boundary Penalties for NN-based PDE Solvers*\
    #text([Machine Learning + X Seminars 2023, Brown University, Providence, online], size: 9pt)
  ],
  [_04/2023_],
)
#entry(
  [
    *Geometry of Sequential Decision Problems*\
    #text([Optimization and Data Science Seminar, University of California, San Diego, online], size: 9pt)
  ],
  [_02/2023_],
)
#entry(
  [
    *Geometry of Natural Policy Gradient Methods*\
    #text([Applied Math Colloquium, University of California, Los Angeles], size: 9pt)
  ],
  [_10/2022_],
)
#entry(
  [
    *The Geometry of Memoryless Stochastic Policy Optimization in Infinite-Horizon POMDPs*\
    #text([Minisymposium on Algebraic Geometry and Machine Learning, SIAM Conference on Mathematics of Data Science], size: 9pt)
  ],
  [_09/2022_],
)
#entry(
  [
    *From Markov Decision Processes to Algebraic Statistics*\
    #text([Workshop on Algebraic Geometry, Combinatorics and Machine Learning, MPI MiS, Leipzig], size: 9pt)
  ],
  [_08/2022_],
)
#entry(
  [
    *The Geometry of Sequential Decision Problems with State Uncertainty*\
    #text([Algebraic Statistics 2022, University of Hawai'i at Manoa, Honolulu], size: 9pt)
  ],
  [_05/2022_],
)
#entry(
  [
    *Deep Ritz Revisited*\
    #text([Math Machine Learning Seminar MPI MiS + UCLA], size: 9pt)
  ],
  [_04/2020_],
)

#subsection("Posters")
#entry(
  [
    *Essentially Sharp Estimates on the Entropy Regularization Error in Discounted Markov Decision Processes*\
    #text([Workshop on Foundations of RL and Control, ICML, Vienna], size: 9pt)
  ],
  [_07/2024_],
)
#entry(
  [
    *Position: Optimization in SciML Should Employ the Function Space Geometry*\
    #text([Forty-first International Conference on Machine Learning, Vienna], size: 9pt)
  ],
  [_07/2024_],
)
#entry(
  [
    *Fisher-Rao Gradient Flows of Linear Programs and State-Action Natural Policy Gradients*\
    #text([Symposium on Sparsity and Singular Structures 2024, RWTH Aachen University], size: 9pt)
  ],
  [_02/2024_],
)
#entry(
  [
    *Geometry and Convergence of Natural Policy Gradient Methods*\
    #text([Symposium on Sparsity and Singular Structures 2024, RWTH Aachen University], size: 9pt)
  ],
  [_02/2024_],
)
#entry(
  [
    *Geometry and Convergence of Natural Policy Gradient Methods*\
    #text([Mini-Workshop on Reinforcement Learning, University of Mannheim], size: 9pt)
  ],
  [_01/2024_],
)
#entry(
  [
    *Solving Infinite-Horizon POMDPs with Memoryless Stochastic Policies in State-Action Space*\
    #text([Multidisciplinary Conference on Reinforcement Learning and Decision Making, Brown University], size: 9pt)
  ],
  [_06/2022_],
)
#entry(
  [
    *The Geometry of Memoryless Stochastic Policy Optimization in Infinite-Horizon POMDPs*\
    #text([International Conference on Learning Representations, online], size: 9pt)
  ],
  [_04/2022_],
)
#entry(
  [
    *A Posteriori Estimates and Convergence Guarantees for Neural Network Based PDE Solvers*\
    #text([Deep Learning and Partial Differential Equations, Isaac Newton Institute, Cambridge, online], size: 9pt)
  ],
  [_11/2021_],
)
#entry(
  [
    *The Geometry of Memoryless Stochastic Policy Optimization in Infinite-Horizon POMDPs*\
    #text([Geometry & Learning from Data, BIRS workshop, Casa Matemática Oaxaca, online], size: 9pt)
  ],
  [_10/2021_],
)
#entry(
  [
    *The Geometry of Discounted Stationary Distributions of Markov Decision Processes*\
    #text([Workshop on Mathematics of Deep Learning, Isaac Newton Institute, Cambridge, online], size: 9pt)
  ],
  [_08/2021_],
)
#entry(
  [
    *The Geometry of Discounted Stationary Distributions of Markov Decision Processes*\
    #text([Conference on Mathematics of Machine Learning, Zentrum für interdisziplinäre Forschung, Bielefeld], size: 9pt)
  ],
  [_08/2021_],
)
#entry(
  [
    *On the Space-Time Expressivity of ResNets*\
    #text([ICLR workshop on Integration of Deep Neural Models and Differential Equations, online], size: 9pt)
  ],
  [_04/2020_],
)
#entry(
  [
    *Deep Ritz Revisited*\
    #text([ICLR workshop on Integration of Deep Neural Models and Differential Equations, online], size: 9pt)
  ],
  [_04/2020_],
)

#section("Skills")
#entry(
  [
    *Languages*: German (mother tongue), English (full working proficiency), French (basic)\
    *Programming*: Julia, Python, R, Mathematica
  ],
  [],
)

#section("Academic references")
- Benjamin Gess, Professor of Mathematics, Technische Universität Berlin, Germany
- Guido Montúfar, Professor of Mathematics, Max-Planck Institute for Mathematics in the Sciences, Leipzig University, Germany
- Holger Rauhut, Professor of Mathematics, Ludwig-Maximilians-Universität München, Germany
// - Semih Çaycı, Junior Professor of Mathematics, RWTH Aachen University, Germany


#section("Publications", note: "In chronological order")
#[
  #set text(size: 10pt)
  // #bibliography("citations.bib", title: none, style: "chicago-author-date.csl", full: true)
]

// #section("Further Commitment")
// #entry(
//   [
//     *Badminton*\
//     Trainer license level B+C\
//     FT Freiburg 1844 honorary Trainer of Children and Adults\
//     TSG Wiesloch honorary Trainer of Children and Adults
//   ],
//   [
//     \
//     _2018/2019_\
//     _since 01/2020_\
//     _2016 - 2019_
//   ],
// )

#section("Community involvement")
#entry(
  [
    *Member of the Promovierendeninitiative*\
    #text([Nationwide council of PhD scholarship holders], size: 9pt)
  ],
  [_2021--2023_],
)
#entry(
  [
    *External PhD representative*, Max Planck Institute for Mathematics in the Sciences
  ],
  [_2021--2022_],
)
#entry(
  [
    *Summer school student organisational committee*, Evangelisches Studienwerk Villigst e.V.
  ],
  [_2018--2019_],
)
#entry(
  [
    *Panel discussion* on _Excellence and Ethics in Science and Academia_\
    #text([75th anniversary ceremonial act of the Evangelisches Studienwerk Villigst e.V.], size: 9pt)
  ],
  [_2023_],
)
#entry(
  [
    *One-week seminar* _Alpha Go -- oder: Vom besiegten Menschen_\
    #text([Annual Summer School of the Evangelisches Studienwerk Villigst e.V.], size: 9pt)
  ],
  [_2019_],
)
