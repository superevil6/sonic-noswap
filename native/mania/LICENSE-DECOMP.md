# Licences for the Sonic Mania part (native/mania/) and the RSDKv5 data reader (tools/rsdk5_extract.py)

NoSwapMania is a code mod for the Sonic Mania decompilation. Its headers mirror the decompilation's structures and
parts of its code follow the decompilation's own (e.g. the Player object), and tools/rsdk5_extract.py ports the RSDKv5
decompilation's data pack reader. Those parts are covered by the two licences below, as they require, on top of NoSwap's
own licence (LICENSE, CC BY-NC-SA 4.0). Both are non-commercial; all of them apply together.

The decompilations and the original code are **not ours**:

- Sonic Mania decompilation: https://github.com/RSDKModding/Sonic-Mania-Decompilation
- RSDKv5(U) decompilation: https://github.com/RSDKModding/RSDKv5-Decompilation
- Original RSDK authors: Evening Star. Decompilation authors: Rubberduckycooly and chuliRMG.
- NoSwapMania builds against RSDKv5-GameAPI (https://github.com/RSDKModding/RSDKv5-GameAPI), which is not included here.

NoSwap ships no prebuilt decompilation and no game assets: players bring their own copy of Sonic Mania and their own
build of the decompilation (the official releases work).

---

# SONIC MANIA DECOMPILATION SOURCE CODE LICENSE v1

The code in this repository is a decompilation of Sonic Mania.
There is original code in this repo, but most of the code is expected to be functionally the same.

This code is provided as-is, that is to say, without liability or warranty. 
Original authors of RSDK and authors of the decompilation are not held responsible for any damages or other claims said.

You may copy, modify, contribute, and distribute, for public or private use, **as long as the following are followed:**
- You may not use the decompilation for commercial (any sort of profit) use.
- You must clearly specify that the decompilation and original code are not yours.
- You may not distribute assets used to run the game not directly provided by the repository (other than unique, modded assets).
- This license must be in all modified copies of source code, and all forks must follow this license.

---

# RSDKv5(U) DECOMPILATION SOURCE CODE LICENSE v2.1

The code in this repository is a decompilation of RSDK (Retro-Engine) version 5 and 5-Ultimate.
There is original code in this repo, but most of the code is to be functionally the same as the version of RSDK this repo specifies.

This code is provided as-is, that is to say, without liability or warranty. 
Original authors of RSDK and authors of the decompilation are not held responsible for any damages or other claims said.

You may copy, modify, contribute, and distribute, for public or private use, **as long as the following are followed:**
- All pre-built executables provided TO ANYONE *PRIVATE OR OTHERWISE* **must be built with DLC disabled by __default.__**
  - DLC is managed by the DummyCore Usercore. A define, `RSDK_AUTOBUILD`, and a CMake flag, `RETRO_DISABLE_PLUS`, are already provided for you to force DLC off.
  - Creating a configuration setting *is allowed,* so long as it is set to off by default.
    - *No such configuration will be pushed to the master repository.*
  - This is to ensure an extra layer of legal protection for Sonic Mania Plus and Sonic Origins Plus.
- You may not use the decompilation for commercial (any sort of profit) use.
- You must clearly specify that the decompilation and original code are not yours: the developers of both must be credited.
- You may not distribute assets used to run any game not directly provided by the repository (other than unique, modded assets).
- This license must be in all modified copies of source code, and all forks must follow this license.

Original RSDK authors: Evening Star

Decompilation authors: Rubberduckycooly and chuliRMG
