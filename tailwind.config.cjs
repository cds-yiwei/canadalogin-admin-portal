/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.{html,js}",
    "./app/static/**/*.{js,html}",
    "./app/controller/**/*.py",
  ],
  theme: {
    extend: {},
  },
  corePlugins: {
    preflight: false,
  },
  plugins: [],
};
