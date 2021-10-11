# create index file of all pdf files in current directory

tree -H '.' -L 1 --noreport --charset utf-8 -P "*.pdf" -o index.html