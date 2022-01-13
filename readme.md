# EBBS Docker Builder

This script is meant to be used by [ebbs](https://github.com/eons-dev/bin_ebbs)

`in_container` is intended to provide ebbs with a means of virtualizing build environments. For example, if you want to build a C++ project as part of your workflow but don't want to go through the work of creating an install script for all the necessary shared libraries your program uses, you can build a docker image with all your code's dependencies met and then use `in_container` to migrate your build process into that virtual environment.