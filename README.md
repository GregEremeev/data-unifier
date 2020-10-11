## data-unifier

#### This library was written as a test task. Code reviewer, enjoy!

#### Some comments
I didn't write tests and made some simplifications to save time.

### Quick start

1 install the library:
```bash
cd data-unifier
pip install -e '.[dev]'
```

2 add local data
```bash
mkdir -p local/data
mv <some_path>/bank1.csv <some_path>/bank2.csv <some_path>/bank3.csv local/data
```

3 Usage
```bash
# the result will be in the file `unified_file.csv`
data_unifier local/data
```

