# ICRA / IROS Controlled Keyword Vocabulary

**Source:** IEEE RAS PaperPlaza keyword list, 2026 cycle. This is the *authoritative* vocabulary — the submission portal requires authors to pick keywords from this list, not to invent them. Papers whose free-form `\begin{IEEEkeywords}` block diverges from PaperPlaza selections may be routed to the wrong area chair.

**When to use:** whenever `TARGET_VENUE = IEEE_CONF` AND the narrative mentions IROS / ICRA / robot / manipulation / locomotion / navigation / teleoperation / sim2real / embodied agent. For non-robotics IEEE conferences (ICC, GLOBECOM, etc.) this vocabulary does not apply.

**ICRA 2027 submission rules (updated):**

1. **Exactly 3 keywords, one per priority tier (1, 2, 3).** You must select one keyword from a priority-1 category, one from priority-2, and one from priority-3. The 3–5 range mentioned below is the general IEEE practice; ICRA 2027 tightened it to exactly 3. (IROS may differ — check the current year's author kit.)
2. **The first keyword (priority 1) becomes the session title.** It should be broad enough to group 4–6 papers (e.g., `Manipulation Planning` or `Deep Learning in Grasping and Manipulation`), not hyper-specific (`In-Hand Manipulation` is too narrow for a session title).
3. **250-character total length limit** across all chosen keywords. Most 3-keyword combinations fit comfortably; watch out if you pick long multi-word terms.
4. **Keywords are locked at submission.** You cannot change them after hitting submit, so run `/pick-keywords` early (during paper-plan or paper-write, not the night before the deadline).
5. Keywords determine reviewer assignment AND your session slot if accepted — picking the wrong first keyword can land you in the wrong track.

**How to use:**

1. Read the abstract / narrative report first.
2. Identify the paper's *primary contribution area* — this determines the **priority-1 keyword** (the session title).
3. Pick one keyword from a priority-2 category that captures the method/approach.
4. Pick one keyword from a priority-3 category for a secondary aspect (e.g., the learning paradigm, sensing modality, or application domain).
5. Verify total character count ≤ 250 (including the keyword strings themselves; PaperPlaza will reject if over).
6. Copy the exact strings into both the LaTeX `\begin{IEEEkeywords}` block AND the PaperPlaza submission form, in the same order (priority 1 → 2 → 3).

**Priority column semantics:** Some categories in the original PaperPlaza list carry a numeric suffix (e.g. "Robot Learning 2", "Robot Learning 3", "Robot Learning 4"). These are the same top-level area split across multiple *priority buckets* used by the program committee for balancing area-chair loads. Priority `1` is the primary bucket for that area; `2`, `3`, `4` are secondary buckets. **For ICRA 2027's "one per tier" rule, treat the SUFFIX NUMBER as the tier**: `Robot Learning` (no suffix) = priority 1, `Robot Learning 2` = priority 2, `Robot Learning 3` = priority 3, `Robot Learning 4` = priority 4 (out of scope for the 3-keyword rule). Categories with no numeric suffix are implicitly priority-1.

---

## Full Vocabulary by Category

### Aerial and Field Robotics

- Demining Systems
- Field Robots
- Marine Robotics
- Mining Robotics
- Space Robotics and Automation

### Aerial Robotics and Distributed Systems

- Aerial Systems: Applications
- Aerial Systems: Mechanics and Control
- Aerial Systems: Perception and Autonomy
- Distributed Robot Systems
- Swarm Robotics

### Applications

- Automation Technologies for Smart Cities
- Education Robotics
- Energy and Environment-Aware Automation
- Environment Monitoring and Management
- Intelligent Transportation Systems
- Robotics and Automation in Agriculture and Forestry
- Robotics and Automation in Construction
- Robotics and Automation in Life Sciences
- Search and Rescue Robots

### Applications 2

- Agricultural Automation
- Art and Entertainment Robotics
- Building Automation
- Industrial Robots
- Product Design, Development and Prototyping
- Robotics in Hazardous Fields
- Robotics in Under-Resourced Settings
- Surveillance Robotic Systems

### Autonomy for Mobility and Manipulation

- Agent-Based Systems
- AI-Based Methods
- Behavior-Based Systems
- Control Architectures and Programming
- Software, Middleware and Programming Environments

### Autonomy for Mobility and Manipulation 2

- AI-Enabled Robotics
- Autonomous Agents
- Object Detection, Segmentation and Categorization
- Reactive and Sensor-Based Planning
- Semantic Scene Understanding

### Cognitive Robotics

- Cognitive Control Architectures
- Cognitive Modeling
- Developmental Robotics
- Embodied Cognitive Science
- Epigenetic Robotics
- Evolutionary Robotics
- Learning from Experience
- Neurorobotics
- Perception-Action Coupling

### Competition Proposal

- Competition

### Human-Centered Robotics and Automation

- Brain-Machine Interfaces
- Haptics and Haptic Interfaces
- Human Factors and Human-in-the-Loop
- Human Performance Augmentation
- Human-Centered Automation
- Human-Centered Robotics
- Physically Assistive Devices
- Telerobotics and Teleoperation
- Virtual Reality and Interfaces
- Wearable Robotics
- Physical Human-Robot Interaction

### Human-Robot Interaction

- Human Detection and Tracking
- Human-Aware Motion Planning
- Human-Robot Collaboration
- Human-Robot Teaming
- Intention Recognition
- Long term Interaction
- Social HRI
- Touch in HRI

### Human-Robot Interaction 2

- Acceptability and Trust
- Design and Human Factors
- Emotional Robotics
- Gesture, Posture and Facial Expressions
- Multi-Modal Perception for HRI
- Natural Dialog for HRI
- Robot Companions
- Safety in HRI

### Humanoids and Animaloids

- Body Balancing
- Climbing Robots
- Cyborgs
- Datasets for Human Motion
- Human and Humanoid Motion Analysis and Synthesis
- Humanoid and Bipedal Locomotion
- Humanoid Robot Systems
- Legged Robots
- Modeling and Simulating Humans
- Multi-Contact Whole-Body Motion Planning and Control
- Natural Machine Motion
- Passive Walking
- Whole-Body Motion Planning and Control

### Localization and Mapping

- Audio-Visual SLAM
- Multi-Robot SLAM
- SLAM
- Visual-Inertial SLAM

### Localization and Mapping 2

- Data Sets for SLAM
- Localization
- Mapping
- Range Sensing
- View Planning for SLAM

### Logistics

- Discrete Event Dynamic Automation Systems
- Factory Automation
- Foundations of Automation
- Health Care Management
- Intelligent and Flexible Manufacturing
- Inventory Management
- Logistics
- Manufacturing, Maintenance and Supply Chains
- Petri Nets for Automation Control
- Planning, Scheduling and Coordination
- Sustainable Production and Service Automation
- Task Planning

### Manipulation and Grasping

- Bimanual Manipulation
- Contact Modeling
- Dual Arm Manipulation
- Grasping
- Grippers and Other End-Effectors
- In-Hand Manipulation
- Manipulation Planning
- Multifingered Hands

### Manipulation and Grasping 2

- Deep Learning in Grasping and Manipulation
- Dexterous Manipulation
- Perception for Grasping and Manipulation
- Mobile Manipulation

### Manufacturing, Process, and Service Automation

- Assembly
- Autonomous Vehicle Navigation
- Compliant Assembly
- Disassembly
- Domestic Robotics
- Force and Tactile Sensing
- Process Control
- Service Robotics

### Mechanisms, Design, and Control

- Actuation and Joint Mechanisms
- Compliance and Impedance Control
- Compliant Joints and Mechanisms
- Failure Detection and Recovery
- Force Control
- Hydraulic/Pneumatic Actuators
- Mechanism Design
- Model Learning for Control
- Motion Control
- Neural and Fuzzy Control
- Redundant Robots
- Robot Safety
- Robust/Adaptive Control
- Tendon/Wire Mechanism

### Medical and Rehabilitation Robotics

- Medical Robots and Systems
- Prosthetics and Exoskeletons
- Rehabilitation Robotics
- Surgical Robotics: Laparoscopy
- Surgical Robotics: Planning
- Surgical Robotics: Steerable Catheters/Needles

### Micro, Nano, and Biomimetic Systems

- Additive Manufacturing
- Automation at Micro-Nano Scales
- Biological Cell Manipulation
- Biologically-Inspired Robots
- Biomimetics
- Micro/Nano Robots
- Nanomanufacturing
- Semiconductor Manufacturing

### Multiple and Distributed Systems

- Cellular and Modular Robots
- Cooperating Robots
- Multi-Robot Systems
- Networked Robots
- Path Planning for Multiple Mobile Robots or Agents
- Sensor Networks

### Planning and Simulation

- Collision Avoidance
- Motion and Path Planning
- Task and Motion Planning

### Planning and Simulation 2

- Computational Geometry
- Constrained Motion Planning
- Integrated Planning and Control
- Integrated Planning and Learning
- Planning under Uncertainty
- Simulation and Animation

### Robot Learning (priority 1)

- Big Data in Robotics and Automation
- Bioinspired Robot Learning
- Data Sets for Robot Learning
- Deep Learning Methods
- Transfer Learning

### Robot Learning 2 (priority 2)

- Reinforcement Learning
- Machine Learning for Robot Control
- Probabilistic Inference
- Sensorimotor Learning

### Robot Learning 3 (priority 3)

- Continual Learning
- Incremental Learning
- Learning Categories and Concepts
- Learning from Demonstration
- Representation Learning

### Robot Learning 4 (priority 4)

- Imitation Learning

### Robotic Systems

- Computer Architecture for Robotic and Automation
- Embedded Systems for Robotic and Automation
- Engineering for Robotic Systems
- Hardware-Software Integration in Robotics
- Methods and Tools for Robot System Design
- Software Architecture for Robotic and Automation
- Software Tools for Benchmarking and Reproducibility
- Software Tools for Robot Programming
- Software-Hardware Integration for Robot Systems

### Soft Robotics

- Modeling, Control, and Learning for Soft Robots
- Soft Robot Applications
- Soft Robot Materials and Design
- Soft Sensors and Actuators

### Theoretical Foundations

- Calibration and Identification
- Dynamics
- Ethics and Philosophy
- Flexible Robotics
- Formal Methods in Robotics and Automation
- Hybrid Logical/Dynamical Planning and Verification
- Kinematics
- Nonholonomic Mechanisms and Systems
- Nonholonomic Motion Planning
- Optimization and Optimal Control
- Parallel Robots
- Performance Evaluation and Benchmarking
- Probability and Statistical Methods
- Underactuated Robots
- Wheeled Robots

### Vision and Sensor-Based Control

- Computer Vision for Medical Robotics
- Omnidirectional Vision
- Sensor Fusion
- Sensor-based Control
- Vision-Based Navigation
- Visual Servoing
- Visual Tracking

### Visual Perception and Learning

- Data Sets for Robotic Vision
- Deep Learning for Visual Perception
- Recognition
- Robot Audition
- Visual Learning

### Visual Perception and Learning 2

- Computer Vision for Automation
- Computer Vision for Manufacturing
- Computer Vision for Transportation
- RGB-D Perception

---

## Quick Alphabetical Lookup (common terms → category)

Use this to check whether a keyword you have in mind is on the list, and which category it belongs to.

- Assembly → Manufacturing, Process, and Service Automation
- Autonomous Vehicle Navigation → Manufacturing, Process, and Service Automation
- Bimanual Manipulation → Manipulation and Grasping
- Collision Avoidance → Planning and Simulation
- Continual Learning → Robot Learning 3
- Deep Learning in Grasping and Manipulation → Manipulation and Grasping 2
- Deep Learning Methods → Robot Learning
- Deep Learning for Visual Perception → Visual Perception and Learning
- Dexterous Manipulation → Manipulation and Grasping 2
- Dual Arm Manipulation → Manipulation and Grasping
- Field Robots → Aerial and Field Robotics
- Grasping → Manipulation and Grasping
- Human-Robot Collaboration → Human-Robot Interaction
- Humanoid Robot Systems → Humanoids and Animaloids
- Imitation Learning → Robot Learning 4
- In-Hand Manipulation → Manipulation and Grasping
- Learning from Demonstration → Robot Learning 3
- Legged Robots → Humanoids and Animaloids
- Localization → Localization and Mapping 2
- Manipulation Planning → Manipulation and Grasping
- Mapping → Localization and Mapping 2
- Medical Robots and Systems → Medical and Rehabilitation Robotics
- Mobile Manipulation → Manipulation and Grasping 2
- Motion and Path Planning → Planning and Simulation
- Multi-Robot Systems → Multiple and Distributed Systems
- Object Detection, Segmentation and Categorization → Autonomy for Mobility and Manipulation 2
- Perception for Grasping and Manipulation → Manipulation and Grasping 2
- Reinforcement Learning → Robot Learning 2
- Representation Learning → Robot Learning 3
- Semantic Scene Understanding → Autonomy for Mobility and Manipulation 2
- Sensor Fusion → Vision and Sensor-Based Control
- SLAM → Localization and Mapping
- Soft Robot Applications → Soft Robotics
- Space Robotics and Automation → Aerial and Field Robotics
- Surgical Robotics: Laparoscopy → Medical and Rehabilitation Robotics
- Swarm Robotics → Aerial Robotics and Distributed Systems
- Task and Motion Planning → Planning and Simulation
- Telerobotics and Teleoperation → Human-Centered Robotics and Automation
- Transfer Learning → Robot Learning
- Vision-Based Navigation → Vision and Sensor-Based Control
- Visual-Inertial SLAM → Localization and Mapping
- Wearable Robotics → Human-Centered Robotics and Automation
- Whole-Body Motion Planning and Control → Humanoids and Animaloids

---

## Selection Heuristics for Common Robotics Papers

- **Manipulation + learning paper (learning to grasp/manipulate objects)** → `Deep Learning in Grasping and Manipulation`, one of `{Grasping, Manipulation Planning, Dexterous Manipulation, Bimanual Manipulation}`, plus one from Robot Learning tier that matches the training paradigm (`Imitation Learning`, `Reinforcement Learning`, `Learning from Demonstration`).
- **VLA / foundation-model robot policy** → `AI-Enabled Robotics`, `Deep Learning Methods`, `Semantic Scene Understanding`, plus a domain keyword (`Mobile Manipulation`, `Autonomous Vehicle Navigation`, ...).
- **Sim-to-real / representation learning for manipulation** → `Representation Learning`, `Transfer Learning`, `Perception for Grasping and Manipulation`.
- **Locomotion (quadruped / bipedal / humanoid)** → `Legged Robots`, `Humanoid and Bipedal Locomotion`, `Reinforcement Learning`, possibly `Whole-Body Motion Planning and Control`.
- **SLAM / navigation** → `SLAM` (or `Visual-Inertial SLAM` / `Multi-Robot SLAM`), `Vision-Based Navigation`, `Mapping`.
- **Assembly / factory / industrial** → `Assembly`, `Industrial Robots`, `Compliance and Impedance Control`, `Force Control`.
- **Human-robot interaction / teleoperation** → `Telerobotics and Teleoperation` or `Physical Human-Robot Interaction`, plus `Human-Robot Collaboration` and one interaction-modality keyword.
- **Surgical robotics** → one of `Surgical Robotics: {Laparoscopy, Planning, Steerable Catheters/Needles}` plus `Medical Robots and Systems` and possibly `Computer Vision for Medical Robotics`.

## Anti-patterns (do not do)

- Picking 5 keywords all from the same sub-category (e.g., `Grasping`, `Dexterous Manipulation`, `Bimanual Manipulation`, `Multifingered Hands`, `In-Hand Manipulation`) — this signals the reviewers "single-topic paper" and wastes 4 keyword slots. Spread across categories.
- Inventing keywords not on this list (e.g., `Diffusion Policy`, `VLA`) — the LaTeX `\begin{IEEEkeywords}` block CAN carry these as informal supplementary terms, but the primary 3–5 keywords must be from this vocabulary because PaperPlaza will only accept those.
- Picking a keyword because it sounds impressive rather than because it matches your contribution (`Cognitive Robotics` for a plain imitation-learning paper).
- Omitting a "learning" keyword when your paper is a learning paper — the area chair uses this to route to reviewers who read learning papers.
