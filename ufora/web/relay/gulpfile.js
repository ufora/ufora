var gulp = require('gulp')
var coffee = require('gulp-coffee')
var concat = require('gulp-concat');
var uglify = require('gulp-uglify');
var sourcemaps = require('gulp-sourcemaps');

var paths = {
    src: [
        'SubscribableWebObjects.coffee',
        'client/**/*.coffee'
        ],
    modules: [
        'node_modules/angular/angular.min.js',
        'node_modules/angular-socket-io/socket.js'
        ]
};


gulp.task('modules', function() {
    return gulp.src(paths.modules)
        .pipe(gulp.dest('public/js'))
});


gulp.task('src', function() {
    return gulp.src(paths.src)
        .pipe(coffee({bare: true}))
        .pipe(sourcemaps.init())
            .pipe(uglify({mangle: false}))
            .pipe(concat('all.min.js'))
        .pipe(sourcemaps.write())
        .pipe(gulp.dest('public/js'));
});

gulp.task('default', ['modules', 'src']);
