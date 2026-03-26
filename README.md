# Elan

![Elan](elan-pic.webp)

Elan is a graph-native orchestration engine for dynamic agent and data workflows.

Built to be flexible and workload-agnostic, it can handle everything from simple scripts to complex workflows whose structure emerges during execution.

Traditional DAG-based orchestrators handle scheduling, retries, and structured workflows well, but offer limited dynamic execution capabilities when the full graph topology is not known ahead of time. Elan takes a different approach: its core model is a dynamic execution graph where branches can expand, recurse, and synchronize as the workflow runs.

Elan also aims to avoid the heavy boilerplate and rigid execution patterns common in many agent frameworks. It is designed to provide a simpler and more coherent orchestration model for multi-step, mixed-workload workflows.

Designed with developer experience in mind, Elan is simple to learn, predictable to operate, and easily moves from local setup to production without over-engineering your codebase. Whether you are coordinating standard Python data tasks or agent loops, Elan provides a consistent interface that scales from a basic script to complex execution graphs.

The name comes from the French word "élan", pronounced "ay-lan" which mean both momentum and moose.
