# Test stand: GPU driver and CUDA software (reported 22.09)

Hardware per the specification (§3.1): Intel Core i7-9700E (8 cores, 2.60 GHz), 128 GiB RAM,
NVIDIA GeForce RTX 4070 Ti SUPER, Ubuntu 22.04.5 LTS, ROS 2 Humble, Docker. The software
below was reported to the team on 22.09 (`nvidia-smi` header and `dpkg -l` rows; to be
confirmed with the organizers, question 8 in [`../QUESTIONS.md`](../QUESTIONS.md)):

```
NVIDIA-SMI 580.173.02             Driver Version: 580.173.02     CUDA Version: 13.0
ii cuda-drivers-575                 575.57.08-0ubuntu1
ii cuda-nvcc-12-9                   12.9.86-1
ii cuda-toolkit-12-9-config-common  12.9.79-1
ii cuda-toolkit-12-config-common    12.9.79-1
ii cuda-toolkit-config-common       12.9.79-1
```

What it means for ReSense:

* The running kernel driver is 580.173.02 (CUDA 13.0 capable) although the installed driver
  package is `cuda-drivers-575`; the toolkit present is CUDA 12.9 (`nvcc` 12.9.86). Any CUDA
  program built against a runtime ≤ 13.0 would run there; a container using the GPU would need
  `nvidia-container-toolkit` on the host and `--gpus all` (or the compose `deploy.resources`
  equivalent).
* **ReSense does not use the GPU.** The image installs no CUDA runtime, the node runs on CPU
  (numpy / scipy / scikit-learn), and nothing in the launch or compose files requests a GPU.
  The stand's driver / toolkit state therefore does not affect the build or the demo; the
  per-frame budget on this machine is the CPU one in [`../EXPERIMENTS.md`](../EXPERIMENTS.md) §3.
* If a GPU stage is ever added (accumulation buffers or a learned second opinion, see
  [`../RESEARCH.md`](../RESEARCH.md) §3–4), it must target CUDA 12.x with the driver above and
  stay optional (CPU fallback), because the spec (§3.1) allows the GPU but does not promise it
  on the control run.
