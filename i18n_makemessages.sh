#/bin/bash

#find . -name "*.py" | xargs xgettext -d fortytwo -o locales/fortytwo.pot

# create new languages:
#export LANG_CODE="ca"
#mkdir -p locales/$LANG_CODE/LC_MESSAGES
#msginit --no-translator -i locales/fortytwo.pot -o locales/$LANG_CODE/LC_MESSAGES/fortytwo.po -l $LANG_CODE


find . -name "*.py" | xargs xgettext -d fortytwo -o locales/fortytwo_new.pot && \
msgmerge --update --backup=none --no-fuzzy-matching locales/fortytwo.pot locales/fortytwo_new.pot && \
rm locales/fortytwo_new.pot

for lang in locales/*/LC_MESSAGES/*.po; do
     msgmerge --update --no-fuzzy-matching --backup=none $lang locales/fortytwo.pot
done

for lang in locales/*/LC_MESSAGES/*.po; do
   msgfmt -o ${lang%.po}.mo $lang
done