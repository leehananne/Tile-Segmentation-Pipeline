# Webserver

This is a simple webserver that serves the tilesets as well as a web page to visualise the tilesets.

## Installation

To install the necessary modules, run

```bash

npm install

```

In `app.js`, add the path of the directory containing the tilesets as an Express static directory. For example, if your directory structure looks like this:

```
.
├── tileset/
└── webserver/
    ├── app.js
    ├── package.json
    └── package-lock.json
```

Add the following line to `app.js`:

```javascript
app.use(express.static("../tileset"));
```

## Usage

To run the server, run

```bash
node app.js
```

or

```bash
npm start
```

or just execute `run.bat`

---

To open the web page, go to [`localhost:3000`](http://localhost:3000) in your browser.

By default, the app will use `3000` as the port. To change the port number, create a `.env` file in the `webserver` directory and set `PORT` to the desired port number. For example, to use port `8080`, create a `.env` file with the following line:

```bash
PORT=8080
```

CesiumJS is used to visualise the tilesets. CesiumJS is installed locally as a Node module, and references to Cesium in `index.html` are achieved by using the module's folders as static directories.

To visualise the metadata, a custom shader is provided which uses `EXT_MESH_FEATURES` to identify `_FEATURE_ID_0` attribute of the models. A button is provided to toggle the shader on and off. If the models do not have the `_FEATURE_ID_0` attribute, the shader will not work and will cause an error.

# Browser-based Visualiser

To retrieve the tiles from the server, within [`index.js`](public/index.js), amend Line 25 with the corresponding name of the tileset JSON.

For instance,

```
.
├── tileset/
│   └── root.json
└── webserver/
    ├── app.js
    ├── package.json
    └── package-lock.json
```

Then inside `index.js`:

```javascript
const tileset = viewer.scene.primitives.add(
    await Cesium.Cesium3DTileset.fromUrl("./root.json")
);
```

will correctly add the tileset into the scene
