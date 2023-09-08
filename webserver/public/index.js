// import * as Cesium from 'cesium';

// Your access token can be found at: https://ion.cesium.com/tokens.
// This is the default access token from your ion account

Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI0YTZhOTAwYy0wMmE2LTQwYWQtOGViZS0xMDM3MDE1ZWQzODkiLCJpZCI6MTU0MzcwLCJpYXQiOjE2ODk1NjQxMTd9.AJHX5iqrqsxONF7D70YuQc5CNYPkG5m4ltTZ4cH8QTg';

// Initialize the Cesium Viewer in the HTML element with the `cesiumContainer` ID.
const viewer = new Cesium.Viewer("cesiumContainer", {
    baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        Cesium.TileMapServiceImageryProvider.fromUrl(
            Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
        )
    ),
    baseLayerPicker: false,
    geocoder: false,
});

// Add Cesium OSM Buildings, a global 3D buildings layer.
// const buildingTileset = await Cesium.createOsmBuildingsAsync();
// viewer.scene.primitives.add(buildingTileset); 

// load 3d tileset data
const tileset = viewer.scene.primitives.add(
    await Cesium.Cesium3DTileset.fromUrl("./extract.json")
);

// fly to singapore
viewer.camera.flyTo({
    destination: new Cesium.Cartesian3.fromDegrees(103.847664, 1.350376, 1000.0),
});

const customShader = new Cesium.CustomShader({
    fragmentShaderText: `
      void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
        int id = fsInput.featureIds.featureId_0;
        vec3 color = vec3(0.0, 0.0, 0.0);
        if (id == 2) {
          color = vec3(0.0, 0.0, 1.0);
        } else if (id == 8) {
          color = vec3(0.0, 1.0, 0.0);
        }
        material.diffuse = color;
      }
    `,
});

// tileset.customShader = customShader;

// add button to toggle custom shader
const button = document.createElement("button");
button.textContent = "Toggle Custom Shader";
button.onclick = () => {
    tileset.customShader = tileset.customShader ? undefined : customShader;
}
viewer.container.appendChild(button);
