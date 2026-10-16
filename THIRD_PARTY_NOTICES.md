# Third-party notices

## Nexora Panel and Nexora Node

This repository is a deployment wrapper. It does **not** contain, patch, rebrand, or redistribute the Nexora executables in Git.

During a private deployment build, the Dockerfile downloads the official release archives directly from:

- Panel: https://github.com/Nexora-VPN/panel/releases/tag/v0.0.4
- Node: https://github.com/Nexora-VPN/node/releases/tag/v0.0.4

The executables are run unchanged. The official Nexora UI, notices, licensing checks, and hardware identity behavior are not modified or bypassed.

Nexora's own terms and license govern use of those components. Review them before deploying:

- Repository: https://github.com/Nexora-VPN/panel
- License: https://github.com/Nexora-VPN/panel/blob/main/LICENSE
- Documentation: https://docs.nexora-panel.org/

CATWOMAN is only the name of this independently written runtime/deployment wrapper and its wrapper-owned default resources.

## Locked release digests

Version `0.0.4`:

| Component | Architecture | SHA-256 |
|---|---|---|
| Nexora Panel | linux/amd64 | `ad7e60b34a93cb3d5dbd28a61ff3e4014c6b8e8be7dac717b68324256b621521` |
| Nexora Node | linux/amd64 | `fa36d9601c6d8fd75fe35206652caa193c4981f25689c11e6414d92a3162bc89` |
| Nexora Panel | linux/arm64 | `6daeace01be843391c6782b26f098e98be73ed2afee23c99c3125b6d8bb53b9c` |
| Nexora Node | linux/arm64 | `48b9547ccb0c041aefaaa231356d43185c28a714d1e3abf9f7468ef5fb8db94a` |

The image is intended for the deployer's own private Railway service. Do not publish or redistribute a built image containing Nexora unless Nexora's license expressly permits it.
