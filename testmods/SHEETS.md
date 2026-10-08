# Where to get each character's sprite sheet

The sprite sheets are the artists' work and are **not** in this repository. Download each one from the page below and
save it under `testmods/` with the file name in the table (the path the character's config reads). Each character's
`SOURCE.txt` has the full credit, the sheet's own terms and what NoSwap does with it; read it before you use a sheet.
Respect every sheet's terms: credit the artists, and never redistribute a sheet against its terms.

Then run `python3 tools/write_configs.py` (it reports any sheet that's missing).

| Character folder | Save as (under `testmods/`) | Download from | Notes |
|---|---|---|---|
| `axel` | `axel/SoR2_Axel.png` | https://www.spriters-resource.com/sega_genesis/sor2/asset/10976/ |  |
| `bark` | `Bark.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/541696/ |  |
| `bean` | `Bean.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/263920/ |  |
| `big` | `Big2.png` | https://www.deviantart.com/ajlew/art/Big-The-Cat-Sprite-Sheet-717939798 |  |
| `blaze` | `blaze/216879.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/216879/ |  |
| `bomb` | `HeavyBomb.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/228293/ | One sheet for Heavy and Bomb. |
| `chaos` | `Chaos.png` | https://www.deviantart.com/ssstgoldy20/art/Sonic-Adventure-Boss-Chaos-0-497339391 | make_configs.py scales a working copy (approved nearest-neighbour exception). |
| `charmy` | `charmy/278731.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/278731/ |  |
| `cream` | `cream/Cream.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/111916/ | make_configs.py makes build/Cream_nocheese.png from it. |
| `ecco` | `ecco/Ecco_TidesOfTime.png` | https://www.spriters-resource.com/sega_genesis/eccothetidesoftime/asset/141831/ |  |
| `emerl` | `Emerl.png`<br>`metal-sonic/249964.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/143123/ | Uses Metal Sonic's sheet too (his Hover balls). |
| `espio` | `espio/Espio.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/228044/ |  |
| `fang` | `fang/224261.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/224261/ |  |
| `flicky` | `Flicky.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/546165/ |  |
| `gamma` | `Gamma2.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/95734/ |  |
| `gilius` | `gilius/Gilius.png`<br>`gilius/Gilius_Magic_GA2.png` | https://www.spriters-resource.com/arcade/goldenaxe/asset/272278/<br>https://www.spriters-resource.com/sega_genesis/goldenaxe2/asset/169246/ | tools/write_configs.py joins the two into gilius/Gilius_sheet.png (make_sheet.py). |
| `headdy` | `headdy/Headdy.png` | https://www.spriters-resource.com/sega_genesis/dynahead/asset/11723/ |  |
| `heavy` | `HeavyBomb.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/228293/ | One sheet for Heavy and Bomb. |
| `honey` | `Honey.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/139745/<br>https://www.deviantart.com/xeric-studios |  |
| `jet` | `jet/Jet.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/96370/ |  |
| `john-morris` | `john-morris/JohnMorris.png`<br>`john-morris/Items.png` | https://www.spriters-resource.com/sega_genesis/cvbl/asset/5797/<br>https://www.spriters-resource.com/sega_genesis/cvbl/asset/5796/ |  |
| `marine` | `Marine.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/111914/ | Also needs marine/anchor_marine.png, the anchor drawn by Superevil (not in the repository yet). |
| `mario` | `Mario.png` | https://www.spriters-resource.com/custom_edited/mariocustoms/asset/202710/ |  |
| `max` | `max/Max.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/222414/ |  |
| `mecha-sonic` | `MechaSonic.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/183703/<br>http://www.themysticalforestzone.com/ |  |
| `megaman` | `megaman/MegaMan.png` | https://www.spriters-resource.com/snes/mm7/asset/31570/ |  |
| `mephiles` | `Mephiles.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/18326/ |  |
| `metal-sonic` | `metal-sonic/249964.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/249964/ |  |
| `mighty` | `mighty/Mighty.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/239838/ |  |
| `nights` | `nights/NiGHTS_S3style.png` | https://www.spriters-resource.com/custom_edited/nightscustoms/asset/16645/ |  |
| `omega` | `Omega.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/18261/ |  |
| `pulseman` | `pulseman/Pulseman.png` | https://www.spriters-resource.com/sega_genesis/pulseman/asset/14343/ |  |
| `ray-poward` | `ray-contra/RayContra.png` | https://www.spriters-resource.com/sega_genesis/contrahc/asset/28048/ | The sheet goes in testmods/ray-contra/ (a folder with no config of its own). |
| `ray` | `ray/Ray.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/227243/ |  |
| `ristar` | `ristar/Ristar_basic.png`<br>`ristar/Ristar_special.png` | http://www.drshnaps.com<br>https://www.spriters-resource.com/sega_genesis/ristar/asset/12659/<br>https://www.spriters-resource.com/sega_genesis/ristar/asset/12660/ | Two sheets: the basic and the special moves. |
| `robotnik` | `robotnik/Robotnik.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/272390/ |  |
| `rouge` | `rouge/565796.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/565796/ |  |
| `sally` | `Sally.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogmediacustoms/asset/156080/ |  |
| `shadow` | `MegamixObjects.png`<br>`ShadowMegamix.png` | https://www.spriters-resource.com/sega_genesis/sonicthehedgehogmegamixhack/asset/97116/<br>https://www.spriters-resource.com/sega_genesis/sonicthehedgehogmegamixhack/asset/97514/ | Two sheets from the Sonic Megamix rips. |
| `shinobi` | `shinobi/Shinobi3_JoeMusashi.png` | https://www.spriters-resource.com/sega_genesis/shinobi3/asset/20808/ |  |
| `silver` | `silver/111917.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/111917/ |  |
| `sparkster` | `sparkster/Sparkster.png` | https://www.spriters-resource.com/sega_genesis/rocketkadventures/asset/29167/ |  |
| `sticks` | `Sticks2.png` | https://www.deviantart.com/silverwarudo33/art/Sticks-Sprite-Sheet-by-NeoFireSonic-848604044 | make_configs.py scales a working copy (approved nearest-neighbour exception). |
| `tails-doll` | `TailsDoll.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/259541/ |  |
| `tikal` | `tikal/Tikal.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/268711/ |  |
| `trip` | `trip/Trip.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/227760/ |  |
| `vector` | `vector/Vector.png` | https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/227570/ |  |

Shared files:

- `_fonts/Sonic1_Fonts_RayanC.png`: the HUD name letters, "Sonic 1 Title Card / HUD / General Font (Expanded)" by
  Rayan C. (Rayan64_C): https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/493842/
- `_shared/mania_ball.png`: cut from your own Sonic Mania by `tools/noswap.py setup` (see the README's build steps).
- Custom move sounds: `testmods/<character>/sfx/SOURCE.txt` names each `.wav` and where it comes from (The Sounds
  Resource).
