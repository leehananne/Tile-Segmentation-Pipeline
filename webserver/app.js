const express = require('express');
const cors = require('cors');

require('dotenv').config();
const PORT = process.env.PORT || 3000;
const app = express();

app.use(express.static('public'));
app.use(express.static('../output'));
// app.use(express.static('../extract'));
// app.use(express.static('../input'));
app.use('/cesium', express.static(__dirname + '/node_modules/cesium/Build/Cesium'));
app.use(cors());

app.get('/', (req, res) => {
    // serve index.html
    res.sendFile(__dirname + '/index.html');
});

app.listen(PORT, () => console.log(`listening on port ${PORT}`));

// Path: index.html
