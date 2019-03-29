#!/bin/sh

for i in $(seq 1 5); do
  /opt/bin/python3 /opt/etc/movies/digitalreleases2.py > /opt/etc/movies/log.txt
  ret=$?
  if [ $ret -eq 0 ]; then
    logger -t "digitalreleases.py" "Загрузка завершена успешно."
    break
  else
    logger -t "digitalreleases.py" "Ошибка загрузки."
  fi
done