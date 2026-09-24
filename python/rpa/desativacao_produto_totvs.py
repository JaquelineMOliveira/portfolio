## Este código é um script de automação RPA (Robotic Process Automation) que busca e altera o status de produtos em uma tabela/grid visual (como no Excel ou em um sistema ERP desktop) utilizando simuladores de teclado e clipboard.

import time
import pyautogui
import pyperclip

def desativar_produto_por_codigo(cod_produto: str, passos_ate_ativo: int = 8) -> str:
    time.sleep(0.5)
    
    encontrou = False
    ultimo_texto = ""
    
    # 1. Varredura vertical na coluna 'Cod.Produto'
    for _ in range(200):
        pyperclip.copy("")  # Limpa o clipboard
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.08)
        
        linha_atual = pyperclip.paste().strip()
        
        # Fim do grid (se a leitura repetir)
        if linha_atual == ultimo_texto and linha_atual != "":
            break
        ultimo_texto = linha_atual
        
        # Se encontrou o código desejado na célula
        if cod_produto in linha_atual:
            encontrou = True
            break
        
        # Desce até a ultima linha registrada
        pyautogui.press('down')
        time.sleep(0.05)

               
    if not encontrou:
        return "nao_encontrado"


    # Avança até a coluna de alteração
    for _ in range(8):
           pyautogui.press('right')
           time.sleep(0.3)
   
    pyautogui.press('2')
    time.sleep(0.3)
   
    for _ in range(9):
           pyautogui.press('left')
           time.sleep(0.2)

    return "ok"


# Exemplo de uso com lista:
if __name__ == "__main__":
    # 1. Defina a sua lista de produtos alvos aqui
    PRODUTOS_ALVOS = ['1020440002' , '1020210002',  '1020170002']

    print("Iniciando em 3 segundos... Certifique-se de que o cursor está na coluna 'Cod.Produto' no TOPO da tabela!")
    time.sleep(3)
    
    # 2. Loop que itera sobre cada produto da lista
    for cod in PRODUTOS_ALVOS:
        print(f"Processando produto: {cod}...")
        
        # Opcional: Se a sua busca sempre precisa começar do início da tabela, 
        # descomente as linhas abaixo para subir até o topo antes de buscar cada item:
        # pyautogui.hotkey('ctrl', 'home')
        # time.sleep(0.5)

        resultado = desativar_produto_por_codigo(cod, passos_ate_ativo=8)
        print(f"Resultado para {cod}: {resultado}")
        time.sleep(0.5)
