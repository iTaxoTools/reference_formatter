# Reference-formatter

This tool formats a list of bibliography reference, given as a txt file, into a consistent style.
The results of formatting are shown in the `Preview` textbox, where they can be corrected and then saved with the `Save` button.

## Dependencies
```
ahocorasick_rs
fuzzywuzzy
pandas
regex
tkinterweb
```

## Configuration

Configuration can be changed in the file `data/config.json`:
* `fuzzy_matching_threshold`: Percentage, above which the titles are considered to be the same, when using fuzzy matching.
