if [ "$TOX_ENV" = "py27" ]
then
   pip install coveralls
   coveralls
fi
