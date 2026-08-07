module.exports = {
  preset: 'react-native',
  setupFiles: ['./jest.setup.js'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|react-native-fs|llama.rn|@react-native-community|react-native-image-picker|react-native-tts)/)',
  ],
};
