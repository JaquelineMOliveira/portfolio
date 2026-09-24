##Abrir e Logar sisttema Totvs

import pyautogui
import time

pyautogui.PAUSE = 0.5
#1.Abrir Chrome e acessar link Totvs
pyautogui.press("win")
pyautogui.write("chrome")
pyautogui.press("enter")

time.sleep(2)
link = "https://teiuindustria163582.protheus.cloudtotvs.com.br:2353/webapp/index.html"
pyautogui.write(link)
pyautogui.press("enter")
time.sleep(2)

#2.Aceitar janelas de acesso iniciais
pyautogui.press("tab",presses=3)
pyautogui.press("enter")


##----------------------------------------------------------------------
## Trecho em Construção #1
##---------------------------------------------------------------------
