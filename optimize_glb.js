// Reduce mesh complexity and re-compress GLB for web preview
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { simplify, textureCompress, draco } = require('@gltf-transform/functions');
const { MeshoptSimplifier } = require('meshoptimizer');

async function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    console.error('Usage: node optimize_glb.js input.glb output.glb');
    process.exit(1);
  }

  const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .setAllowHTTP(true);

  console.log('Reading', inputPath);
  const document = await io.read(inputPath);

  console.log('Simplifying mesh...');
  await document.transform(
    simplify({ simplifier: MeshoptSimplifier, ratio: 0.25, error: 0.05 }),
    textureCompress({ targetFormat: 'webp', quality: 75, resize: [1024, 1024] }),
    draco({ compressionLevel: 10 })
  );

  console.log('Writing', outputPath);
  await io.write(outputPath, document);
  console.log('Done.');
}

main().catch(e => { console.error(e); process.exit(1); });
