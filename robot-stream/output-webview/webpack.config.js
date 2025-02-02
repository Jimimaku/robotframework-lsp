const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = (env) => {
    let mode;
    let devtool;
    let minimize;

    if (env.production) {
        console.log("Building in PRODUCTION mode!");

        mode = "production";
        devtool = false;
        minimize = true;
    } else if (env.development) {
        console.log("Building in DEV mode!");
        mode = "development";
        // devtool = 'cheap-module-source-map';
        // devtool = 'eval';
        devtool = "source-map";
        minimize = false;
    } else {
        throw Error("Either production or development need to be specified");
    }

    target = path.resolve(__dirname, "dist");
    let envTarget = env.target;
    if (envTarget) {
        target = envTarget;
    }
    console.log("Building to: " + target);

    return {
        entry: ["./src/index.ts", "./src/style.css"],
        output: {
            filename: "bundle.js",
            path: target,
            clean: true,
        },
        devtool: devtool,
        module: {
            rules: [
                {
                    test: /\.css$/,
                    use: [
                        {
                            loader: "style-loader",
                            options: {
                                insert: "head", // Insert style tag inside of <head>
                                injectType: "singletonStyleTag", // Wrap all  style in just one style tag
                            },
                        },
                        "css-loader",
                    ],
                },
                {
                    test: /\.(png|svg|jpg|jpeg|gif)$/i,
                    type: "asset/inline",
                },
                {
                    test: /\.ts$/,
                    use: "ts-loader",
                    exclude: /node_modules/,
                },
                {
                    test: /\.(woff|woff2|eot|ttf|otf)$/i,
                    type: "asset/inline",
                },
            ],
        },
        resolve: {
            extensions: [".ts", ".js"],
        },
        plugins: [
            // Generates the index.html
            new HtmlWebpackPlugin({
                title: "Robot Output",
                template: "./src/index.html",
                scriptLoading: "blocking",
            }),
        ],
        optimization: {
            minimize: minimize,
        },
        mode: mode,
        devServer: {
            contentBase: "./",
        },
    };
};
