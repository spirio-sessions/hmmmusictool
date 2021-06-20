const webpack = require('webpack');

const PROD = process.argv.indexOf('-p') !== -1;

module.exports = {
    'context': __dirname,
    entry: {
        'Main': 'src/FeatureTest',
    },
    output: {
        filename: './build/[name].js',
        chunkFilename: './build/[id].js',
        sourceMapFilename: '[file].map',
    },
    resolve: {
        root: __dirname,
        modulesDirectories: ['node_modules', 'src', 'third_party', 'node_modules/tone', 'style'],
    },
    plugins: PROD ? [
        new webpack.optimize.UglifyJsPlugin({minimize: true}),
        new webpack.DefinePlugin({
            // http://ml0.informatik.fh-nuernberg.de:60003
            WEBSOCKETS_API: JSON.stringify('/'),
            REST_API: JSON.stringify('http://127.0.0.1:8080'),
            USE_WEBSOCKETS: JSON.stringify(true),
        })
    ] : [],
    module: {
        loaders: [
            {
                test: /\.js$/,
                exclude: /(node_modules|Tone\.js)/,
                loader: 'babel', // 'babel-loader' is also a valid name to reference
                query: {
                    presets: ['es2015']
                }
            },
            {
                test: /\.css$/,
                loader: 'style!css!autoprefixer!sass'
            },
            {
                test: /\.json$/,
                loader: 'json-loader'
            },
            {
                test: /\.(png|gif|svg)$/,
                loader: 'url-loader',
            },
            {
                test: /\.(ttf|eot|woff(2)?)(\?[a-z0-9]+)?$/,
                loader: 'file-loader?name=images/font/[hash].[ext]'
            }
        ]
    },
    devtool: PROD ? '' : '#eval-source-map'
};
