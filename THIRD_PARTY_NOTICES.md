# External applications and protocol references

This repository contains independently authored bridge code and documentation. It does not distribute ArtCraft application binaries, upstream source files, font files, upstream sample projects or imported third-party artwork. It does include selected original test exports and one app-window screenshot as documented below.

ArtCraft Crafting Apps are external applications maintained by their respective upstream authors. Users obtain and license those apps separately. The bridge's license does not grant rights to the apps, brands, protocol documents, imported media or generated exports. This project is independently maintained and is not an official ArtCraft or Recraft product.

The adapter was implemented against documented local control behavior. References include

- [ArtCraft application site](https://getartcraft.com/apps/designcraft)
- [PhotoCraft control protocol](https://github.com/storytold/photocraft/blob/main/docs/control-protocol.md)
- [DesignCraft control protocol](https://github.com/storytold/designcraft/blob/main/docs/control-protocol.md)
- [VectorCraft control protocol](https://github.com/storytold/vectorcraft/blob/main/docs/control-protocol.md)
- [PdfCraft v0.6.0 control implementation](https://github.com/storytold/pdfcraft/blob/v0.6.0/crates/ui-egui/src/control.rs)

No upstream implementation is vendored. The runtime uses Python's standard library. Packaging uses setuptools as a build tool; CI uses GitHub Actions maintained separately under their own terms. PdfCraft portable mode operates on a local copy of a user-installed app and does not redistribute that copy.

## Included CADCraft preview

`docs/images/cadcraft-cube.png` is a native CADCraft render of the original cube defined by this repository’s example code. It contains only that synthetic geometry, with no imported assets, application chrome, private drawing or embedded text metadata. This project-owned example image is included under the repository’s MIT license.

`docs/images/cadcraft-solid-stl.png` is an independently plotted preview of the original example mesh, generated using matplotlib. It contains no imported artwork or app UI. It and the synthetic example geometry are repository-owned MIT example assets. Trimesh and matplotlib were used separately for verification/preview only; they are not shipped or runtime dependencies.

## Included creative workflow evidence

The print layout, vector design, motion graphics and rocket geometry are original examples created for this project. `docs/images/app-tests/photocraft.png` shows a native PhotoCraft composition using an original architectural source generated with OpenAI ImageGen. ImageGen generated the source photograph; the native app performed collage composition, masks, transforms and text. `lightcraft.jpg` is the native LightCraft graded export of that composition. The original photo source and fonts are not redistributed here.

`designcraft.png`, `photocraft.png`, `vectorcraft.png`, `lightcraft.jpg`, `filmcraft.png` and `effectcraft.png` are exports/previews of the original examples. `rocket.png` is an independent matplotlib visualization of the actual mesh reopened from CADCraft, with illustrative colors. `docs/models/rocket.stl` is the original example geometry, serialized from the reexecuted public example's CADCraft readback. These project-owned assets are included under MIT; generated imagery is disclosed as such without claiming exclusivity over generated content.

`pdfcraft.png` is a native PdfCraft window screenshot displaying the original test poster. Its app interface and marks remain attributable to the external application and subject to its own terms; the repository's MIT license does not relicense that interface. The screenshot is included as documentation of the local test, with no private document or workstation path visible.

`docs/media/filmcraft-after-hours.mp4` and `effectcraft-after-hours.mp4` contain original silent title graphics created and exported in the respective apps. No source footage, audio recordings or app binaries are included. The installed font files are not distributed. Native text rendering in previews and videos does not bundle the font programs.

Image and video metadata was inspected before publication. PNG gamma/color data, matplotlib software provenance and native media encoder fields may be retained; no control tokens, local user paths, private source-photo prompts or personal metadata are included in these public exports. Verification tools (trimesh, Pillow, matplotlib, ffprobe/ffmpeg) remain separate from the dependency-free bridge runtime.

The VectorCraft PNG retains its nonpersonal `source.svg` title and test creation timestamp. LightCraft JPEG retains orientation, LightCraft CreatorTool/Software, sRGB profile and resolution metadata; matplotlib previews retain tool attribution. macOS provenance extended attributes were inspected locally and are not stored in Git blobs. None of the included image exports contains signed C2PA credentials.
