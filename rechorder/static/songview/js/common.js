var key_names = ['A', 'B\u266d', 'B', 'C', 'C\u266f', 'D', 'E\u266d', 'E', 'F', 'F\u266f', 'G', 'A\u266d']

function pC(c) {
    return c.replace('b', '\u266d').replace('#', '\u266f')
}

function n2c(n) {
    return key_names[n % 12];
}