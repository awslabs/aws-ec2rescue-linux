#!/bin/bash

for file in `find . -type f -name "*yaml"`; do
    grep -L package $file
done