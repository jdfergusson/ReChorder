// Increase Handler
function _fsIncrease(opt) {;
    size = parseFloat($(opt.selector).css("font-size"));
    size = Math.min(size + opt.sizeInterval, opt.sizeMaximum);
    _fsRender(opt, size);
}

// Decrease Handler
function _fsDecrease(opt) {
    size = parseFloat($(opt.selector).css("font-size"));
    size = Math.max(size - opt.sizeInterval, opt.sizeMinimum);
    _fsRender(opt, size);
}

// Reset Handler
function _fsReset(opt) {
    _fsRender(opt, opt.sizeDefault);
}

function _fsToggleChords() {
    disabled = JSON.parse(localStorage.getItem('chords-disabled'));
    console.log(disabled);
    if (disabled) {
        // Was disabled, so enable it
        localStorage.setItem('chords-disabled', JSON.stringify(false));
    }
    else
    {
        // Wasn't disabled, also default behaviour
        localStorage.setItem('chords-disabled', JSON.stringify(true));
    }
    _fsShowOrHideChords();
}

function _fsShowOrHideChords() {
    disabled = JSON.parse(localStorage.getItem('chords-disabled'));
    if (disabled) {
        $('.block-chord').hide()
        $('#fs-c-eye-on').hide()
        $('#fs-c-eye-off').show()
    }
    else
    {
        $('.block-chord').show()
        $('#fs-c-eye-on').show()
        $('#fs-c-eye-off').hide()
    }
}

// Render
function _fsRender(opt, size) {
    $(opt.selector).css("font-size", size +"px");
    $(opt.buttonIncrease).prop("disabled", (size >= opt.sizeMaximum));
    $(opt.buttonDecrease).prop("disabled", size <= opt.sizeMinimum);
    $(opt.buttonReset).prop("disabled", (size == opt.sizeDefault));
    localStorage.setItem(opt.cookieName, size);
}

var _fs_chord_opt = {
    selector:      ".block-chord",
    sizeMaximum:    48,
    sizeDefault:    20,
    sizeMinimum:    8,
    sizeInterval:   2,
    buttonIncrease: "#fs-c-increase",
    buttonDecrease: "#fs-c-decrease",
    buttonReset:    "#fs-c-reset",
    buttonToggle:   "#fs-c-toggle",
    cookieName:     "font-size-chords",
}

var _fs_lyrics_opt = {
    selector:      ".block-lyric",
    sizeMaximum:    48,
    sizeDefault:    18,
    sizeMinimum:    8,
    sizeInterval:   2,
    buttonIncrease: "#fs-l-increase",
    buttonDecrease: "#fs-l-decrease",
    buttonReset:    "#fs-l-reset",
    cookieName:     "font-size-lyrics",
}

function fsGo() {
    _fsRender(_fs_chord_opt, localStorage.getItem(_fs_chord_opt.cookieName) || _fs_chord_opt.sizeDefault);
    _fsRender(_fs_lyrics_opt,  localStorage.getItem(_fs_lyrics_opt.cookieName) || _fs_lyrics_opt.sizeDefault);
}

$(function() {
    // Initialize
    $(_fs_chord_opt.buttonIncrease).click(function() {_fsIncrease(_fs_chord_opt);});
    $(_fs_chord_opt.buttonDecrease).click(function() {_fsDecrease(_fs_chord_opt);});
    $(_fs_chord_opt.buttonReset).click(function() {_fsReset(_fs_chord_opt);});
    $(_fs_chord_opt.buttonToggle).click(_fsToggleChords);


    $(_fs_lyrics_opt.buttonIncrease).click(function() {_fsIncrease(_fs_lyrics_opt);});
    $(_fs_lyrics_opt.buttonDecrease).click(function() {_fsDecrease(_fs_lyrics_opt);});
    $(_fs_lyrics_opt.buttonReset).click(function() {_fsReset(_fs_lyrics_opt);});

    fsGo();
    _fsShowOrHideChords();
});