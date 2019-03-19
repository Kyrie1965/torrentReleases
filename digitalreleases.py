### DAYS — за сколько последних дней загружать цифровые релизы. По умолчанию 60.
### SOCKS_IP и SOCKS_PORT — IP-адрес и порт SOCKS Proxy. Если они указаны, то будет импортирована библиотека (PySocks), а в функции rutorLinks запросы будет обрабатываться через указанный прокси-сервер. В digitalReleases и filmDetail запросы всегда идут без прокси.
### SORT_TYPE — тип финальной сортировки. rating — сортировка по рейтингу, releaseDate — сортировка по дате цифрового релиза, torrentsDate — сортировка по дате появления торрента.
### USE_MAGNET — использование Magnet-ссылок вместо ссылок на торрент-файлы.


### digitalReleases(days) возвращает массив со словарями {filmID, releaseDate}, цифровые релизы за количество дней days.
### filmDetail(filmID) возвращает словарь с информацией по фильму, соответствующему filmID.
### rutorLinks(filmID) возвращает словарь с раздачами, соответствующими filmID.
### saveHTML(movies, filePath) формирует HTML-файл по пути filePath из массива movies.
### main объединяет всё вместе digitalReleases > rutorLinks + filmDetail > saveHTML.

DAYS = 60
USE_MAGNET = False
SORT_TYPE = "rating"
SOCKS_IP = ""
SOCKS_PORT = 0
HTML_SAVE_PATH = "/opt/share/www/releases.html"
#HTML_SAVE_PATH = r"C:\Users\Yuri\releases.html"


KINOPOISK_UUID = "6730382b7a236cd964264b49413ed00f" ### Генерируется автоматически в main, но можно в случае необходимости использовать константные значения.
KINOPOISK_CLIENTID = "56decdcf6d4ad1bcaa1b3856" ### Генерируется автоматически в main, но можно в случае необходимости использовать константные значения.
KINOPOISK_API_SALT = "IDATevHDS7"
KINOPOISK_BASE_URL = "https://ma.kinopoisk.ru"
KINOPOISK_API_RELEAESES = "/k/v1/films/releases/digital?digitalReleaseMonth={}&limit=1000&offset=0&uuid={}"
KINOPOISK_BASE_URL2 = "https://ma.kinopoisk.ru/ios/5.0.0/"
KINOPOISK_API_FILMDETAIL = "getKPFilmDetailView?still_limit=9&filmID={}&uuid={}"
POSTER_URL = "https://st.kp.yandex.net/images/{}{}width=360"
RUTOR_BASE_URL = "http://rutor.info/search/0/0/010/0/film%20"

import hashlib
import datetime
import urllib.request
from urllib.parse import urljoin 
import time
import gzip
import json
import html
import re
import operator
import os
import binascii
if SOCKS_IP:
	import socks
	import socket

def digitalReleases(days):
	rDict = {}
	result = []
	
	currentDateReal = datetime.date.today()
	currentDate = currentDateReal + datetime.timedelta(days=7)

	print("Текущая дата (с запасом 7 дней): " + currentDate.strftime("%d.%m.%Y"))
	downloadDates =[currentDate]
	targetDate = datetime.date.today() - datetime.timedelta(days=days)
	print("Целевая дата: " + targetDate.strftime("%d.%m.%Y"))
	iterationDate = datetime.date.today() + datetime.timedelta(days=7)
	
	while (targetDate.year != iterationDate.year) or (targetDate.month != iterationDate.month):
		iterationDate = iterationDate.replace(day=1) - datetime.timedelta(days=1)
		downloadDates.append(iterationDate)
	
	print("Количество месяцев для загрузки: " + str(len(downloadDates)))
	
	for downloadDate in downloadDates:
		print("Загрузка релизов за " + downloadDate.strftime("%m.%Y") + ".")
		
		requestMethod = KINOPOISK_API_RELEAESES.format(downloadDate.strftime("%m.%Y"), KINOPOISK_UUID)
		timestamp = str(int(round(time.time() * 1000)))
		hashString = requestMethod + timestamp + KINOPOISK_API_SALT
		
		request = urllib.request.Request(KINOPOISK_BASE_URL + requestMethod)
		request.add_header("Accept-encoding", "gzip")
		request.add_header("Accept", "application/json")
		request.add_header("User-Agent", "Android client (6.0.1 / api23), ru.kinopoisk/4.6.5 (86)")
		request.add_header("Image-Scale", "3")
		request.add_header("device", "android")
		request.add_header("ClientId", KINOPOISK_CLIENTID)
		request.add_header("countryID", "2")
		request.add_header("cityID", "1")
		request.add_header("Android-Api-Version", "23")
		request.add_header("clientDate", datetime.date.today().strftime("%H:%M %d.%m.%Y"))
		request.add_header("X-TIMESTAMP", timestamp)
		request.add_header("X-SIGNATURE", hashlib.md5(hashString.encode('utf-8')).hexdigest())
		
		try:
			response = urllib.request.urlopen(request)
		except Exception:
			print("Ошибка соединения при загрузке релизов за " + downloadDate.strftime("%m.%Y") + ". Даём второй шанс.")
			response = urllib.request.urlopen(request)
		
		if response.info().get('Content-Encoding') == 'gzip':
			gzipFile = gzip.GzipFile(fileobj=response)
			content = gzipFile.read().decode("utf-8")
		else:
			content = response.read().decode("utf-8")
		
		if content:
			tmpDict = json.loads(content)
			if not tmpDict:
				raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Ответ не соответствует JSON.")
			if tmpDict.get("success") != True:
				raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". В ответе нет значения success или оно равно False.")
			items = tmpDict.get("data")
			if items == None or not isinstance(items, dict):
				raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Проблемы со значением data.")
			items = items.get("items")
			if items == None or not isinstance(items, list):
				raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Проблемы со значением items.")
			
			for item in items:
				if not isinstance(item, dict):
					raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Проблемы с одним из элементов items.")
				filmID = item.get("id")
				if not isinstance(filmID, int):
					raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Проблемы с id в одном из элементов items.")
				contextData = item.get("contextData")
				if not isinstance(contextData, dict):
					raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Проблемы с contextData в одном из элементов items.")
				releaseDateStr = contextData.get("releaseDate")
				if not isinstance(releaseDateStr, str):
					raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ". Проблемы с releaseDate в одном из элементов items.")
				releaseDate = datetime.datetime.strptime(releaseDateStr, "%Y-%m-%d").date()
				
				if (targetDate <= releaseDate) and (releaseDate <= currentDate):
					rDict[str(filmID)] = releaseDate
		else:
			raise ValueError("Ошибка загрузки релизов за " + downloadDate.strftime("%m.%Y") + ".")
	
	print("Загружены ID от {} релизов.".format(len(rDict)))
	
	for key, value in rDict.items():
		temp = {"filmID": key, "releaseDate":value}
		result.append(temp)
		
	return result

def filmDetail(filmID):
	print("Загрузка данных для filmID " + filmID + ".")
	
	result = {}
	
	requestMethod = KINOPOISK_API_FILMDETAIL.format(filmID, KINOPOISK_UUID)
	timestamp = str(int(round(time.time() * 1000)))
	hashString = requestMethod + timestamp + KINOPOISK_API_SALT
	
	request = urllib.request.Request(KINOPOISK_BASE_URL2 + requestMethod)
	request.add_header("Accept-encoding", "gzip")
	request.add_header("Accept", "application/json")
	request.add_header("User-Agent", "Android client (6.0.1 / api23), ru.kinopoisk/4.6.5 (86)")
	request.add_header("Image-Scale", "3")
	request.add_header("device", "android")
	request.add_header("ClientId", KINOPOISK_CLIENTID)
	request.add_header("countryID", "2")
	request.add_header("cityID", "1")
	request.add_header("Android-Api-Version", "23")
	request.add_header("clientDate", datetime.date.today().strftime("%H:%M %d.%m.%Y"))
	request.add_header("X-TIMESTAMP", timestamp)
	request.add_header("X-SIGNATURE", hashlib.md5(hashString.encode('utf-8')).hexdigest())
	
	try:
		response = urllib.request.urlopen(request)
	except Exception:
		print("Ошибка соединения при загрузке данных для filmID " + filmID + ". Даём второй шанс.")
		response = urllib.request.urlopen(request)

	if response.info().get('Content-Encoding') == 'gzip':
		gzipFile = gzip.GzipFile(fileobj=response)
		content = gzipFile.read().decode("utf-8")
	else:
		content = response.read().decode("utf-8")
	
	if content:
		tmpDict = json.loads(content)
		#print(tmpDict)

		if not tmpDict:
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Ответ не соответствует JSON.")
		if tmpDict.get("resultCode") != 0:
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". В ответе нет значения resultCode или оно не равно 0.")
		itemData = tmpDict.get("data")
		if itemData == None or not isinstance(itemData, dict):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением data.")
		nameRU = itemData.get("nameRU")
		if nameRU == None or not isinstance(nameRU, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением nameRU.")
		nameEN = itemData.get("nameEN")
		if nameEN == None or not isinstance(nameEN, str):
			nameEN = ""
		year = itemData.get("year")
		if year == None or not isinstance(year, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением year.")
		country = itemData.get("country")
		if country == None or not isinstance(country, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением country.")
		genre = itemData.get("genre")
		if genre == None or not isinstance(genre, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением genre.")
		description = itemData.get("description")
		if description == None or not isinstance(description, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением description.")
		ratingAgeLimits = itemData.get("ratingAgeLimits")
		if ratingAgeLimits == None or not isinstance(ratingAgeLimits, str):
			ratingAgeLimits = ""
		posterURL = itemData.get("posterURL")
		if posterURL == None or not isinstance(posterURL, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением posterURL.")
		if "?" in posterURL:
			posterURL = POSTER_URL.format(posterURL, "&")
		else:
			posterURL = POSTER_URL.format(posterURL, "?")
		filmLength = itemData.get("filmLength")
		if filmLength == None or not isinstance(filmLength, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением filmLength.")
		ratingData = itemData.get("ratingData")
		if ratingData == None or not isinstance(ratingData, dict):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением ratingData.")
		ratingKP = ratingData.get("rating")
		if ratingKP == None or not isinstance(ratingKP, str):
			ratingKP = "0"
		ratingIMDb = ratingData.get("ratingIMDb")
		if ratingIMDb == None or not isinstance(ratingIMDb, str):
			ratingIMDb = ""
		webURL = itemData.get("webURL")
		if webURL == None or not isinstance(webURL, str):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением webURL.")

		
		directors = []
		actors = []
		
		creators = itemData.get("creators")
		if creators == None or not isinstance(creators, list):
			raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением creators.")
		for personsGroup in creators:
			if not isinstance(personsGroup, list):
				raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением creators > personsGroup.")
			for person in personsGroup:
				if not isinstance(person, dict):
					raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением creators > personsGroup > person.")
				if person.get("professionKey") == "director":
					if person.get("nameRU"):
						directors.append(person.get("nameRU"))
				if person.get("professionKey") == "actor":
					if person.get("nameRU"):
						actors.append(person.get("nameRU"))
	else:
		raise ValueError("Ошибка загрузки данных для filmID " + filmID + ".")
	
	if ratingIMDb and ratingKP:
		rating = "{0:.1f}".format((float(ratingKP) + float(ratingIMDb)) / 2.0 + 0.001)
	else:
		rating = ratingKP
	
	directorsResult = ""
	if len(directors) > 0:
		for director in directors:
			directorsResult += director
			directorsResult += ", "
	if directorsResult.endswith(", "):
		directorsResult = directorsResult[:-2]
	
	actorsResult = ""
	if len(actors) > 0:
		for actor in actors:
			actorsResult += actor
			actorsResult += ", "
	if actorsResult.endswith(", "):
		actorsResult = actorsResult[:-2]
	
	result["filmID"] = filmID
	result["nameRU"] = nameRU
	result["nameOriginal"] = nameEN
	result["description"] = description
	result["year"] = year
	result["country"] = country
	result["genre"] = genre
	result["ratingAgeLimits"] = ratingAgeLimits
	result["posterURL"] = posterURL
	result["filmLength"] = filmLength
	result["ratingKP"] = ratingKP
	result["ratingIMDb"] = ratingIMDb
	result["rating"] = rating
	result["ratingFloat"] = float(rating)
	result["directors"] = directorsResult
	result["actors"] = actorsResult
	result["webURL"] = webURL

	
	#print(result)
	
	return result

def rutorLinks(filmID):
	print("Загрузка торрент-ссылок для filmID " + filmID + ".")
	
	if SOCKS_IP:
		default_socket = socket.socket
		socks.set_default_proxy(socks.SOCKS5, SOCKS_IP, SOCKS_PORT)
		socket.socket = socks.socksocket

	request = urllib.request.Request(RUTOR_BASE_URL + filmID)
	request.add_header("Accept-encoding", "gzip")
	request.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0")
	
	try:
		response = urllib.request.urlopen(request)
	except Exception:
		print("Ошибка соединения при загрузке торрент-ссылок для filmID " + filmID + ". Даём второй шанс.")
		response = urllib.request.urlopen(request)
	if response.info().get('Content-Encoding') == 'gzip':
		gzipFile = gzip.GzipFile(fileobj=response)
		content = gzipFile.read().decode("utf-8")
	else:
		content = response.read().decode("utf-8")
	
	if SOCKS_IP:
		socket.socket = default_socket
	
	strIndex = content.find("<div id=\"index\">")
	if strIndex != -1:
		content = content[strIndex:]
	else:
		raise IndexError("Ошибка загрузки торрент-ссылок для filmID " + filmID + ". Не найден блок с торрентами. Возможно, сайт rutor заблокирован.")
	
	strIndex = content.find("</div>")
	if strIndex != -1:
		content = content[:-(len(content) - strIndex)]
	else:
		raise IndexError("Ошибка загрузки торрент-ссылок для filmID " + filmID + ". Не найден блок с торрентами. Возможно, сайт rutor заблокирован.")
	
	patternLink = re.compile("<a class=\"downgif\" href=\"(.*?)\">")
	matches1 = re.findall(patternLink, content)
	patternName = re.compile("<a href=\"/torrent/(.*?)\">(.*?)</a>")
	matches2 = re.findall(patternName, content)
	patternSeeders = re.compile("alt=\"S\" />(.*?)</span>")
	matches3 = re.findall(patternSeeders, content)
	patternMagnet = re.compile("<a href=\"magnet:(.*?)\">")
	matches4 = re.findall(patternMagnet, content)
	patternDate = re.compile("<td>(.*?)</td><td ") #09&nbsp;Мар&nbsp;19
	matches5 = re.findall(patternDate, content)
	#print(str(len(matches1)) + " " + str(len(matches2)) + " " +str(len(matches3)) + " " + str(len(matches4)) + " " + str(len(matches5)))
	if (len(matches1) != len(matches2)) or (len(matches1) != len(matches3)) or (len(matches1) != len(matches4)) or (len(matches1) != len(matches4)) or (len(matches1) != len(matches5)):
		raise IndexError("Ошибка загрузки торрент-ссылок для filmID " + filmID + ". Неверный формат блока с торрентами.")
		
	months = {"Янв": 1, "Фев": 2, "Мар": 3, "Апр": 4, "Май": 5, "Июн": 6, "Июл": 7, "Авг": 8, "Сен": 9, "Окт": 10, "Ноя": 11, "Дек": 12}
	
	allTorrents = []
	for i in range(len(matches1)):
		link = matches1[i].strip()
		if not link.startswith("http"):
			link = urljoin("http://rutor.info", link)
		dateStr = matches5[i].strip()
		components = dateStr.split("&nbsp;")
		if (len(components) != 3):
			raise ValueError("Ошибка загрузки торрент-ссылок для filmID " + filmID + ". Неверный формат даты.")
		torrentDate = datetime.date(int(components[2]), months[components[1]], int(components[0]))
		#print(torrentDate)
		tmpDict = {"link": link, "name": html.unescape(matches2[i][1]).strip(), "seeders": int(html.unescape(matches3[i]).strip()), "magnet": "magnet:" + (matches4[i]).strip(), "date": torrentDate}
		allTorrents.append(tmpDict)
	
	result = {}
	
	for item in allTorrents:
		tmpParts = item["name"].split("|")
		if len(tmpParts) == 1:
			continue
		
		realName = tmpParts[0].strip().upper()
		tags = set()
		
		for i in range(1, len(tmpParts)):
			tmpParts2 = tmpParts[i].split(",")
			for tmpPart in tmpParts2:
				tags.add(tmpPart.strip().upper())
		
		if ("LINE" in tags) or ("UKR" in tags) or ("3D-VIDEO" in tags) or ("60 FPS" in tags):
			continue
					
		if not (("ЛИЦЕНЗИЯ" in tags) or ("ITUNES" in tags) or ("D" in tags) or ("D2" in tags)):
			continue
						
		if "UHD BDREMUX" in realName:
			if "HDR" in tags:
				if result.get("UHD BDRemux HDR") != None:
					if item["seeders"] > result["UHD BDRemux HDR"]["seeders"]:
						result["UHD BDRemux HDR"] = item #{"link": item["link"], "magnet": item["magnet"],  "seeders": item["seeders"]}
				else:
					result["UHD BDRemux HDR"] = item
				#print("!UHD BDRemux HDR: " + tmpParts[0])
			else:
				if result.get("UHD BDRemux SDR") != None:
					if item["seeders"] > result["UHD BDRemux SDR"]["seeders"]:
						result["UHD BDRemux SDR"] = item
				else:
					result["UHD BDRemux SDR"] = item
				#print("!UHD BDRemux SDR: " + tmpParts[0])
		elif "BDREMUX" in realName:
			if result.get("BDRemux") != None:
				if item["seeders"] > result["BDRemux"]["seeders"]:
					result["BDRemux"] = item
			else:
				result["BDRemux"] = item
			#print("!BDRemux: " + tmpParts[0])
		elif "BDRIP-HEVC 1080" in realName:
			if result.get("BDRip-HEVC 1080p") != None:
				if item["seeders"] > result["BDRip-HEVC 1080p"]["seeders"]:
					result["BDRip-HEVC 1080p"] = item
			else:
				result["BDRip-HEVC 1080p"] = item
			#print("!BDRip-HEVC 1080p: " + tmpParts[0])
		elif "BDRIP 1080" in realName:
			if result.get("BDRip 1080p") != None:
				if item["seeders"] > result["BDRip 1080p"]["seeders"]:
					result["BDRip 1080p"] = item
			else:
				result["BDRip 1080p"] = item
			#print("!BDRip 1080p: " + tmpParts[0])
		elif "WEB-DL 2160" in realName:
			if "HDR" in tags:
				if result.get("WEB-DL 2160p HDR") != None:
					if item["seeders"] > result["WEB-DL 2160p HDR"]["seeders"]:
						result["WEB-DL 2160p HDR"] = item
				else:
					result["WEB-DL 2160p HDR"] = item
				#print("!WEB-DL 2160p HDR: " + tmpParts[0])
			else:
				if result.get("WEB-DL 2160p SDR") != None:
					if item["seeders"] > result["WEB-DL 2160p SDR"]["seeders"]:
						result["WEB-DL 2160p SDR"] = item
				else:
					result["WEB-DL 2160p SDR"] = item
				#print("!WEB-DL 2160p SDR: " + tmpParts[0])
		elif "WEB-DL 1080" in realName:
			if result.get("WEB-DL 1080p") != None:
				if item["seeders"] > result["WEB-DL 1080p"]["seeders"]:
					result["WEB-DL 1080p"] = item
			else:
				result["WEB-DL 1080p"] = item
			#print("!WEB-DL 1080p: " + tmpParts[0])
	
	if result.get("UHD BDRemux HDR") or result.get("UHD BDRemux SDR") or result.get("BDRip-HEVC 1080p") or result.get("BDRip 1080p"):
		result.pop("WEB-DL 2160p HDR", None)
		result.pop("WEB-DL 2160p SDR", None)
		result.pop("WEB-DL 1080p", None)
	
	finalResult = []
	
	if result.get("WEB-DL 1080p"):
		finalResult.append({"link": result["WEB-DL 1080p"]["link"], "magnet": result["WEB-DL 1080p"]["magnet"], "date": result["WEB-DL 1080p"]["date"], "type": "WEB-DL 1080p"})
	if result.get("WEB-DL 2160p HDR"):
		finalResult.append({"link": result["WEB-DL 2160p HDR"]["link"], "magnet": result["WEB-DL 2160p HDR"]["magnet"], "date": result["WEB-DL 2160p HDR"]["date"], "type": "WEB-DL 2160p HDR"})
	elif result.get("WEB-DL 2160p SDR"):
		finalResult.append({"link": result["WEB-DL 2160p SDR"]["link"], "magnet": result["WEB-DL 2160p SDR"]["magnet"], "date": result["WEB-DL 2160p SDR"]["date"], "type": "WEB-DL 2160p SDR"})
	if result.get("BDRip 1080p"):
		finalResult.append({"link": result["BDRip 1080p"]["link"], "magnet": result["BDRip 1080p"]["magnet"], "date": result["BDRip 1080p"]["date"], "type": "BDRip 1080p"})
	if result.get("BDRip-HEVC 1080p"):
		finalResult.append({"link": result["BDRip-HEVC 1080p"]["link"], "magnet": result["BDRip-HEVC 1080p"]["magnet"], "date": result["BDRip-HEVC 1080p"]["date"], "type": "BDRip-HEVC 1080p"})
	if result.get("BDRemux"):
		finalResult.append({"link": result["BDRemux"]["link"], "magnet": result["BDRemux"]["magnet"], "date": result["BDRemux"]["date"], "type": "BDRemux"})
	if result.get("UHD BDRemux HDR"):
		finalResult.append({"link": result["UHD BDRemux HDR"]["link"], "magnet": result["UHD BDRemux HDR"]["magnet"], "date": result["UHD BDRemux HDR"]["date"], "type": "UHD BDRemux HDR"})
	elif result.get("UHD BDRemux SDR"):
		finalResult.append({"link": result["UHD BDRemux SDR"]["link"], "magnet": result["UHD BDRemux SDR"]["magnet"], "date": result["UHD BDRemux SDR"]["date"], "type": "UHD BDRemux SDR"})

	#print(finalResult)
		
	return finalResult

def saveHTML(movies, filePath):
	f = open(filePath,'w', encoding='utf-8')
	html =  """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="ru-RU">
<head>
<meta charset="utf-8">
<meta content="width=960" name="viewport">
<title>Новые цифровые релизы</title>
<style type="text/css">
  html {
      background-color: #e6e6e6;
      min-width: 1024px;
      width: 100%;
      position: relative;
  }

  body {
      background: #e6e6e6;
      color: #333;
      font-family: tahoma,verdana,arial;
      margin: 0;
      padding: 0 0 22px 0;
  }

  * {
      outline: 0;
  }

  .shadow {
      box-shadow: 0px 10px 20px 0px rgba(0, 0, 0, 0.2);
      width: 850px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
  }

  .block1 {
      width: 850px;
      position: relative;
      margin: 0 auto;
  }

  .block2 {
      position: relative;
      background-color: #f2f2f2;
      width: 100%;
  }

  .block2::before, .block2::after {
      content: "";
      display: table;
  }

  .block2::after, .photoInfoTable::after {
      clear: both;
  }

  .photoInfoTable::before, .photoInfoTable::after {
      content: "";
      display: table;
  }

  .photoInfoTable {
      width: 850px;
      float: left;
  }

  .headerFilm h1 {
      margin: 0;
      padding: 0;
  }

  .headerFilm {
      width: 620px;
      padding: 20px 20px 20px 15px;
      position: relative;
  }


  H1.moviename {
      vertical-align: middle;
      padding-left: 0px;
      margin: 5px 0;
      font-size: 25px;
      font-weight: normal;
  }

  H1 {
      font-size: 25px;
      font-weight: normal;
      color: #000;
  }

  .headerFilm > span {
      color: #666;
      font-size: 13px;
  }

  .film-img-box {
      margin-left: 0;
      position: relative;
      left: -12px;
      min-height: 205px;
      margin-bottom: 15px;
  }

  .film-img-box img {
      border: 0;
  }

  .photoBlock {
      width: 210px;
      padding: 0 0 0 0;
      float: left;
      position: relative;
      font-size: 11px;
  }

  .movie-buttons-container {
      margin-bottom: 20px;
  }

  .torrentbutton {
      cursor: pointer;
      border: none;
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
      background-color: #f60;
      border-radius: 3px;
      color: #fff;
      display: block;
      font: 12px Arial, sans-serif;
      font-weight: normal;
      line-height: normal;
      font-weight: bold;
      height: 35px;
      line-height: 36px;
      -webkit-transition: background-color 0.1s, color 0.1s, border-color 0.1s;
      -moz-transition: background-color 0.1s, color 0.1s, border-color 0.1s;
      transition: background-color 0.1s, color 0.1s, border-color 0.1s;
      text-align: center;
      text-decoration: none;
      width: 160px;
      margin: 10px 0 10px 15px;
      display:inline-block;
  }

  .infoTable {
      float: left;
      display: block;
  }

  .infoTable .info {
      width: 465px;
  }

  .info, .info * {
      border-collapse: collapse;
      margin: 0;
      padding: 0;
  }

  .info tr {
      border-bottom: #DFDFDF solid 1px; 
  }

  .info .type {
      color: #f60;
      width: 119px;
      padding-left: 23px;
  }

  .info td {
      min-height: 14px;
      vertical-align: top;
      padding-bottom: 9px;
      padding: 6px 0 6px 20px;
  }

  td {
      font-family: tahoma,verdana,arial;
      font-size: 11px;
      color: #000;
  }

  .film-rating {
      border-radius: 1px;
      position: absolute;
      left: 5px;
      top: 5px;
      z-index: 5;
      box-shadow: none;
      color: #fff;
      width: 32px;
      font-size: 11px;
      font-weight: 600;
      line-height: 13px;
      padding: 3px 0 2px;
      text-align: center;
      font-family: Arial,Tahoma,Verdana,sans-serif;
  }
</style>
</head>
<body>
  <div class="shadow">
    <div class="block1" style="background-color: #f2f2f2;">"""
	descriptionTemplate = """
                <tr>
                  <td class="type">{}</td>
                  <td>
                    <div style="position: relative">
                        {}
                    </div>
                  </td>
                </tr>"""
	buttonsTemplate = """          <button class="torrentbutton" style="" onclick="location.href='{}'">{}</button>"""
	movieTemplate = """      <div class="block2">
        <div class="photoInfoTable">
          <div class="headerFilm">
            <h1 class="moviename" itemprop="name">{}</h1>
            <span itemprop="alternativeHeadline" style="{}">{}</span>
          </div>
          <div class="photoBlock">
            <div class="film-img-box">
              <div class="film-rating" style="background-color: {};">{}</div> <!-- #3bb33b > 7 #aaa; -->
              <img src="{}" alt="{}" itemprop="image" width="205"></img>
            </div>
          </div>
          <div class="infoTable">
            <table class="info">
              <tbody>
{}
              </tbody>
            </table>
          </div>
        </div>
        <div class="movie-buttons-container">
{}
        </div>
      </div>
"""
	for movie in movies:
		#print(movie["nameRU"])
		#print(movie["torrentsDate"])
		#print(movie["releaseDate"])
		descriptionBlock = ""
		descriptionBlock += descriptionTemplate.format("год", movie["year"])
		descriptionBlock += descriptionTemplate.format("страна", movie["country"])
		descriptionBlock += descriptionTemplate.format("режиссёр", movie["directors"])
		descriptionBlock += descriptionTemplate.format("актёры", movie["actors"])
		descriptionBlock += descriptionTemplate.format("жанр", movie["genre"])
		if len(movie["ratingAgeLimits"]) > 0:
			descriptionBlock += descriptionTemplate.format("возраст", movie["ratingAgeLimits"] + " и старше")
		descriptionBlock += descriptionTemplate.format("продолжительность", movie["filmLength"])
		descriptionBlock += descriptionTemplate.format("рейтинг КиноПоиск", "<a href=\"{}\" style=\"text-decoration: underline; color:black\">{}</a>".format(movie["webURL"], movie["ratingKP"]))
		if len(movie["ratingIMDb"]) > 0:
			descriptionBlock += descriptionTemplate.format("рейтинг IMDb", movie["ratingIMDb"])
		descriptionBlock += descriptionTemplate.format("цифровой релиз", movie["releaseDate"].strftime("%d.%m.%Y"))
		descriptionBlock += descriptionTemplate.format("описание", movie["description"])
		
		torrents = movie["torrents"]
		buttonsBlock = "" 
		for torrent in torrents:
			if USE_MAGNET:
				buttonsBlock += buttonsTemplate.format(torrent["magnet"], torrent["type"])
			else:
				buttonsBlock += buttonsTemplate.format(torrent["link"], torrent["type"])
		
		displayOrigName = "display: none;"
		if len(movie["nameOriginal"]) > 0:
			displayOrigName = ""
			
		ratingColor = "#aaa"
		if movie["ratingFloat"] >= 7:
			ratingColor = "#3bb33b"
		elif movie["ratingFloat"] < 5.5:
			ratingColor = "#b43c3c"
			
		html += movieTemplate.format(movie["nameRU"], displayOrigName, movie["nameOriginal"], ratingColor, movie["rating"], movie["posterURL"], movie["nameRU"], descriptionBlock, buttonsBlock)
		
	html += """    </div>
  </div>
</body>
</html>"""
	f.write(html)
	f.close()
	return 

def main():
	KINOPOISK_UUID = binascii.b2a_hex(os.urandom(16))
	KINOPOISK_CLIENTID = binascii.b2a_hex(os.urandom(12))
	
	releases = digitalReleases(DAYS)
	movies = []

	for release in releases:
		torrents = rutorLinks(release["filmID"])
		if len(torrents) == 0:
			continue
		
		dates = []
		for torrent in torrents:
			dates.append(torrent["date"])
		dates.sort()
		
		detail = filmDetail(release["filmID"])
		detail["releaseDate"] = release["releaseDate"]
		detail["torrents"] = torrents
		detail["torrentsDate"] = dates[0]
		movies.append(detail)
	
	if (SORT_TYPE == "rating"):
		movies.sort(key = operator.itemgetter("ratingFloat"), reverse = True)
	elif (SORT_TYPE == "torrentsDate"):
		movies.sort(key = operator.itemgetter("torrentsDate"), reverse = True)
	else:
		movies.sort(key = operator.itemgetter("releaseDate"), reverse = True)
	
	saveHTML(movies, HTML_SAVE_PATH)
	
main()