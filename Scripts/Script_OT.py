# -*- coding: utf-8 -*-
import os
import sys
import random
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchWindowException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
import time
import sqlite3
import multiprocessing
import threading

municipios_pendientes = multiprocessing.Value('i', 0)  # Contador compartido
terminar_procesos = multiprocessing.Event()  # Evento para señalar la terminación

def human_like_delay():
    time.sleep(random.uniform(1.5, 4))

def random_mouse_movement(driver):
    action = ActionChains(driver)
    action.move_by_offset(random.randint(-100, 100), random.randint(-100, 100)).perform()
    human_like_delay()

def simulate_human_behavior(driver):
    random_mouse_movement(driver)
    if random.random() < 0.3:  # 30% de probabilidad de hacer scroll
        driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
    human_like_delay()

def setup_driver(download_path):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.popups": 2,
        "profile.default_content_setting_values.geolocation": 2,
        
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def human_like_input(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.1))

def iniciar_sesion(driver, usuario, contraseña):
    ventana_original = driver.current_window_handle
    WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div/div/div[3]/a"))).click()
    human_like_delay()
    WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.ID, "loginBtn"))).click()
    human_like_delay()
    WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div[2]/div[1]/div/div/div[1]/form/ul/li[4]/button"))).click()
    human_like_delay()
    driver.switch_to.window(driver.window_handles[-1])

    email_input = WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.NAME, "loginfmt")))
    human_like_input(email_input, usuario)
    email_input.send_keys(Keys.RETURN)
    human_like_delay()

    password_input = WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.NAME, "passwd")))
    human_like_input(password_input, contraseña)
    password_input.send_keys(Keys.RETURN)
    human_like_delay()

    webdriver.ActionChains(driver).send_keys(Keys.RETURN).perform()
    human_like_delay()
    driver.switch_to.window(ventana_original)

def get_db_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    db_dir = os.path.join(parent_dir, 'db')
    return os.path.join(db_dir, 'Consultas.db')

def get_next_municipio(lock):
    with lock:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT municipio FROM municipios_tab LIMIT 1")
        municipio = cursor.fetchone()
        if municipio:
            municipio = municipio[0]
            cursor.execute("DELETE FROM municipios_tab WHERE municipio = ?", (municipio,))
            
            conn.commit()
            municipios_pendientes.value -= 1  # Decrementar el contador
            if municipios_pendientes.value == 0:
                terminar_procesos.set()  # Señalar que todos los municipios han sido procesados
        conn.close()
        return municipio

def actualizar_total_descargados(municipio, total_descargados):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE municipios_tab_replica SET total_descargados = ? WHERE municipio = ?", (total_descargados, municipio))
        conn.commit()
        print(f"Base de datos actualizada para {municipio}")
    except sqlite3.Error as e:
        print(f"Error al actualizar la base de datos: {e}")
    finally:
        conn.close()

def generar_descargas_folder(municipio):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    descargas_dir = os.path.join(parent_dir, 'Descargas', municipio)
    os.makedirs(descargas_dir, exist_ok=True)
    return descargas_dir

def sanitize_filename(filename):
    return filename.replace(':', '-').replace('/', '_').replace('\\', '_')

def buscar_municipio(driver, municipio):
    select_field = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "span.select2-selection.select2-selection--single"))
    )
    select_field.click()
    human_like_delay()
    
    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/span/span/span[1]/input"))
    )
    search_input.clear()
    human_like_input(search_input, municipio)
    human_like_delay()
    search_input.send_keys(Keys.ENTER)
    human_like_delay()

def paginacion_maxima(driver):
    time.sleep(2)
    try:
        select_rangoMax_documentos = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#docViewPage > a:nth-child(3)"))
        )
        select_rangoMax_documentos.click()
        human_like_delay()
    except TimeoutException:
        print("Tiempo de espera agotado al buscar el elemento para clic")
    except NoSuchElementException:
        print("No se encontró el elemento para clic")
    except Exception as e:
        print(f"Error inesperado en clic_rango_max_documentos: {str(e)}")

def consultas_descargas(driver, municipio):
    try:
        # Obtener el número de resultados
        resultados_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[4]/div[2]/div[1]"))
        )
        resultados_texto = resultados_element.text
        numero_resultados = int(''.join(filter(str.isdigit, resultados_texto)))
        
        print(f"Número de resultados para {municipio}: {numero_resultados}")
        
        # Actualizar la base de datos
        db_path = get_db_path()
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE municipios_tab_replica SET objetivo_descargas = ? WHERE municipio = ?", (numero_resultados, municipio))
            conn.commit()
            print(f"Base de datos actualizada exitosamente para {municipio}")
        except sqlite3.Error as e:
            print(f"Error al actualizar la base de datos para {municipio}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
    
    except TimeoutException:
        print(f"Tiempo de espera agotado al buscar elementos para {municipio}")
    except NoSuchElementException:
        print(f"No se encontró algún elemento necesario para {municipio}")
    except Exception as e:
        print(f"Error inesperado en consultas_descargas para {municipio}: {str(e)}")

def is_download_completed(temp_dir):
    for filename in os.listdir(temp_dir):
        if filename.endswith('.crdownload'):
            return False
    return True

def process_cards(driver, descargas_dir, municipio, temp_dir):
    card_index = 1
    archivos_no_procesados = []
    informe_path = os.path.join(os.path.dirname(descargas_dir), 'informe_archivos_no_procesados.txt')

    while True:
        try:
            driver.execute_script(f"window.scrollTo(0, {random.randint(100, 300)});")
            human_like_delay()

            card_xpath = f"/html/body/div[2]/div[4]/div[4]/div[{card_index}]"
            card = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, card_xpath)))
            
            action = ActionChains(driver)
            action.move_to_element(card).move_by_offset(random.randint(-50, 50), random.randint(-20, 20)).perform()
            human_like_delay()

            title_xpath = f"{card_xpath}/div/div[2]/div/div/div[1]/div"
            title_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, title_xpath)))
            title = title_element.text
            print(f" Procesando: {title} Del Municipio: {municipio} - Posicion Actual: {card_index}")

            potential_file_name = sanitize_filename(f"{title}")
            potential_file_path = os.path.join(descargas_dir, potential_file_name)
            
            # Comprobar si existe algún archivo con el mismo nombre y cualquier extensión
            if any(os.path.exists(f"{potential_file_path}.{ext}") for ext in ['pdf', 'zip', 'rar', '7z', 'dwg', 'jpg', 'tif', 'tiff', 'prn','bmp','cdr','WOR','xls','xlsx']):
                print(f"Un archivo con el nombre '{potential_file_name}' (con cualquier extensión) ya existe. Pasando al siguiente.")
                card_index += 1
                continue

            view_button_xpath = f"{card_xpath}//button[contains(@class, 'btn-default')]"
            view_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, view_button_xpath)))
            view_button.click()

            max_wait = 7200  # 2 horas de espera máxima
            check_interval = 3  # Verificar cada 10 segundos
            start_time = time.time()
            downloaded_file = None

            while time.time() - start_time < max_wait:
                if is_download_completed(temp_dir):
                    files = [f for f in os.listdir(temp_dir) if not f.endswith('.crdownload')]
                    if files:
                        downloaded_file = os.path.join(temp_dir, max(files, key=lambda f: os.path.getmtime(os.path.join(temp_dir, f))))
                        break
                tiempo_transcurrido= int(time.time() - start_time)
                if tiempo_transcurrido == 120 or tiempo_transcurrido == 360 or tiempo_transcurrido == 3600:
                    print(f"Esperando descarga para {title}... Tiempo transcurrido: {int(time.time() - start_time)} segundos")
                time.sleep(check_interval)

            if downloaded_file:
                time.sleep(5)
                file_name = os.path.basename(downloaded_file)
                file_ext = os.path.splitext(file_name)[1]
                
                new_file_name = sanitize_filename(f"{title}{file_ext}")
                destino_final = os.path.join(descargas_dir, new_file_name)
                
                counter = 1
                while os.path.exists(destino_final):
                    name, ext = os.path.splitext(new_file_name)
                    destino_final = os.path.join(descargas_dir, f"{name}_{counter}{ext}")
                    counter += 1

                shutil.move(downloaded_file, destino_final)
                print(f"Archivo descargado y movido: {new_file_name}")
            else:
                print(f"No se pudo descargar el archivo para: {title} después de {max_wait} segundos")
                archivos_no_procesados.append(f"{municipio}: {title} - Tiempo de espera agotado")

            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))

            card_index += 1
            human_like_delay()

        except (NoSuchElementException, TimeoutException):
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "tableDocumentos_next"))
                )
                
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)
                
                if next_button.is_displayed() and next_button.is_enabled() and "disabled" not in next_button.get_attribute("class"):
                    driver.execute_script("arguments[0].click();", next_button)
                    print("Pasando a la siguiente página de resultados.")
                    card_index = 1
                else:
                    print("El botón 'Siguiente' no es visible, habilitado, o está deshabilitado.")
                    break
            except (NoSuchElementException, TimeoutException):
                print("No se encontró el botón 'Siguiente' o no está disponible.")
                break
            except ElementNotInteractableException:
                print("El botón 'Siguiente' no es interactuable en este momento.")
                break

        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            archivos_no_procesados.append(f"{municipio}: Error - {str(e)}")
            continue

    print(f"Consultas para {municipio} completado.")

    total_descargados = len([f for f in os.listdir(descargas_dir) if os.path.isfile(os.path.join(descargas_dir, f))])
    print(f"Total de archivos descargados para {municipio}: {total_descargados}")

    actualizar_total_descargados(municipio, total_descargados)

    with open(informe_path, 'a', encoding='utf-8') as f:
        for archivo in archivos_no_procesados:
            f.write(f"{archivo}\n")
"""          
def cargar_credenciales():
    with open('credentials.txt', 'r') as file:
        lines = file.readlines()
        email = lines[0].split(': ')[1].strip()
        password = lines[1].split(': ')[1].strip()
    return email, password
"""

def cargar_credenciales():
    # Obtiene la ruta absoluta del script que se está ejecutando
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Se mueve dos niveles arriba (fuera de la carpeta Scripts, a la raíz del proyecto)
    #project_root = os.path.dirname(os.path.dirname(script_dir))

    # Se mueve un nivel arriba (fuera de la carpeta Scripts)
    project_root = os.path.dirname(script_dir)   
    # Construye la ruta completa al archivo credentials.txt
    credentials_file_path = os.path.join(project_root, 'credentials.txt')
    
    # Lee el archivo credentials.txt
    with open(credentials_file_path, 'r') as file:
        lines = file.readlines()
        email = lines[0].split(': ')[1].strip()
        password = lines[1].split(': ')[1].strip()
    
    return email, password
def definir_workers():
    # Obtiene la ruta absoluta del script que se está ejecutando
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Se mueve un nivel arriba (fuera de la carpeta Scripts)
    project_root = os.path.dirname(script_dir)
    
    # Construye la ruta completa al archivo workers_ventanas.txt
    workers_file_path = os.path.join(project_root, 'workers_ventanas.txt')
    
    # Lee el archivo workers_ventanas.txt
    with open(workers_file_path, 'r') as file:
        lines = file.readlines()
        workers = lines[0].strip()
        print(f'Cantidad de Ventanas para Consultas: {workers} Ventanas/Workers')
    
    return workers

def process_municipio(process_id, lock, delay):
    time.sleep(delay)
    max_retries = 10
    retry_count = 0

    while retry_count < max_retries and not terminar_procesos.is_set():
        try:
            temp_dir = os.path.join(os.getcwd(), 'temp', f'temp{process_id}')
            os.makedirs(temp_dir, exist_ok=True)

            driver = setup_driver(temp_dir)
            driver.get("https://www.colombiaot.gov.co/pot/buscador.html")
            usuario, contraseña = cargar_credenciales()
            iniciar_sesion(driver, usuario, contraseña)

            while not terminar_procesos.is_set():
                municipio = get_next_municipio(lock)
                if not municipio:
                    time.sleep(1)  # Esperar un poco antes de verificar de nuevo
                    continue

                try:
                    driver.get("https://www.colombiaot.gov.co/pot/buscador.html")
                    time.sleep(3)
                    ventana_original = driver.current_window_handle
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div/div/div[3]/a"))).click()
                    human_like_delay()
                    time.sleep(1)
                    descargas_dir = generar_descargas_folder(municipio)
                    buscar_municipio(driver, municipio)
                    print(f"Proceso {process_id}: Búsqueda realizada para: {municipio}")
                    paginacion_maxima(driver)
                    consultas_descargas(driver,municipio)
                    process_cards(driver, descargas_dir, municipio, temp_dir)
                    time.sleep(2)
                    human_like_delay()
                except Exception as e:
                    print(f"Proceso {process_id}: Error al procesar el municipio {municipio}: {str(e)}")
                    with lock:
                        db_path = get_db_path()
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO municipios_tab (municipio) VALUES (?)", (municipio,))
                        conn.commit()
                        conn.close()
                        municipios_pendientes.value += 1  # Incrementar el contador al devolver el municipio
                    continue

            driver.quit()
            shutil.rmtree(temp_dir)
            print(f"Proceso {process_id} completado con éxito.")
            break  # Salir del bucle de reintentos si todo fue bien

        except Exception as e:
            retry_count += 1
            print(f"Proceso {process_id} falló. Intento {retry_count} de {max_retries}. Error: {str(e)}")
            time.sleep(10)  # Esperar antes de reintentar

    if retry_count == max_retries:
        print(f"Proceso {process_id} falló después de {max_retries} intentos.")

def main():
    num_processes = int(definir_workers())
    lock = multiprocessing.Lock()

    # Inicializar el contador de municipios pendientes
    with lock:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM municipios_tab")
        count = cursor.fetchone()[0]
        conn.close()
        municipios_pendientes.value = count

    processes = []
    for i in range(num_processes):
        delay = i * 32  # 30 segundos de retraso entre cada inicio de proceso
        p = multiprocessing.Process(target=process_municipio, args=(i+1, lock, delay))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print("Todos los procesos han terminado.")

if __name__ == "__main__":
    main()