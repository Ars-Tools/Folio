export default {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {}, // autoprefixer is usually included or unnecessary if browserslist is handled by lightningcss/etc, but keeping it is safe
  },
}
