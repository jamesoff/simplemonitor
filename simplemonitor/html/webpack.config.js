module.exports = {
  entry: {
    main: "./src/index.js",
    maps: "./src/maps.js",
  },
  output: {
    filename: "[name].bundle.js",
  },
  module: {
    rules: [
      {
        test: /\.css$/,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.png$/,
        type: "asset/resource",
      },
    ],
  },
  resolve: {
    alias: {
      jquery: "jquery/dist/jquery.slim.js",
    },
  },
  mode: "production",
};
