# External applications and protocol references

This repository contains independently authored bridge code and documentation. It does not distribute ArtCraft application binaries, upstream source files, fonts, sample projects or third-party artwork.

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
