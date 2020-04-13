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

// Render
function _fsRender(opt, size) {
    $(opt.selector).css("font-size", size +"px");
    $(opt.buttonIncrease).prop( "disabled", (size >= opt.sizeMaximum) );
    $(opt.buttonDecrease).prop( "disabled", size <= opt.sizeMinimum );
    $(opt.buttonReset).prop( "disabled", (size == opt.sizeDefault) );
    $.cookie(opt.cookieName, size);
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

$(function() {
    // Initialize
    $(_fs_chord_opt.buttonIncrease).click(function() {_fsIncrease(_fs_chord_opt);});
    $(_fs_chord_opt.buttonDecrease).click(function() {_fsDecrease(_fs_chord_opt);});
    $(_fs_chord_opt.buttonReset).click(function() {_fsReset(_fs_chord_opt);});

    $(_fs_lyrics_opt.buttonIncrease).click(function() {_fsIncrease(_fs_lyrics_opt);});
    $(_fs_lyrics_opt.buttonDecrease).click(function() {_fsDecrease(_fs_lyrics_opt);});
    $(_fs_lyrics_opt.buttonReset).click(function() {_fsReset(_fs_lyrics_opt);});

    _fsRender(_fs_chord_opt,  $.cookie(_fs_chord_opt.cookieName) || _fs_chord_opt.sizeDefault);
    _fsRender(_fs_lyrics_opt,  $.cookie(_fs_lyrics_opt.cookieName) || _fs_lyrics_opt.sizeDefault);
});