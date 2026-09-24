# O trecho atual está composto por digitar e buscar e abrir para edição a tabela de preço

# Trecho a ser substituido com issue #2 --------------------------------------------------
print("Você tem 5 segundos para colocar o foco na tela do Protheus e clicar no campo")
time.sleep(5)
#---------------------------------------------------------------------------------------
tabela = 'C09'
pyautogui.write(tabela, interval=0.05)
pyautogui.press("enter",presses=2)
time.sleep(2)
pyautogui.press("a") #Abri tabela para alterar
time.sleep(2)
