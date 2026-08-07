jest.mock('react-native-fs', () => ({
  DocumentDirectoryPath: '/mock/documents',
  stat: jest.fn().mockResolvedValue({ size: 0 }),
  exists: jest.fn().mockResolvedValue(false),
  unlink: jest.fn().mockResolvedValue(undefined),
  moveFile: jest.fn().mockResolvedValue(undefined),
  downloadFile: jest.fn(() => ({
    promise: Promise.resolve({ statusCode: 200 }),
  })),
}));

jest.mock('llama.rn', () => ({
  initLlama: jest.fn(async () => ({
    initMultimodal: jest.fn(async () => undefined),
    completion: jest.fn(async () => undefined),
    release: jest.fn(async () => undefined),
  })),
  getBackendDevicesInfo: jest.fn(async () => []),
}));

jest.mock('react-native-tts', () => ({
  setDefaultLanguage: jest.fn(),
  setDefaultRate: jest.fn(),
  addEventListener: jest.fn(),
  stop: jest.fn(async () => undefined),
  speak: jest.fn(async () => undefined),
}));

jest.mock('@react-native-community/voice', () => ({
  onSpeechResults: null,
  onSpeechError: null,
  start: jest.fn(async () => undefined),
  stop: jest.fn(async () => ({})),
}));

jest.mock('react-native-image-picker', () => ({
  launchImageLibrary: jest.fn((_opts, cb) => cb({ didCancel: true })),
  launchCamera: jest.fn((_opts, cb) => cb({ didCancel: true })),
}));
