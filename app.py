import sys
import os
import html
import getpass
import webbrowser
from functools import partial
from datetime import datetime

from armazenamento import (
    FicheiroCorrompido, ler_json, alterar_lista, filtrar_dashboards, email_valido
)

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QScrollArea, QGraphicsDropShadowEffect, QTextEdit,
    QMessageBox, QFrame, QLineEdit, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

APP_NAME = "Power BI Launcher"

# Pasta onde ficam os ficheiros json (dashboards e feedback).
# Por defeito é a pasta "dados" ao lado deste ficheiro. Se quiseres que
# vários utilizadores partilhem o mesmo feedback, aponta para uma pasta
# na rede com a variável de ambiente LAUNCHER_DADOS.
PASTA_DADOS = os.environ.get("LAUNCHER_DADOS") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dados")
FICHEIRO_DASHBOARDS = os.path.join(PASTA_DADOS, "dashboards.json")
FICHEIRO_FEEDBACK = os.path.join(PASTA_DADOS, "feedback.json")

# Opcional: restringe os links a certos domínios, separados por vírgula
# (ex.: LAUNCHER_HOSTS=app.powerbi.com,powerbi.com). Em qualquer caso só se
# aceitam links https.
HOSTS_PERMITIDOS = tuple(h.strip().lower() for h in
                         os.environ.get("LAUNCHER_HOSTS", "").split(",") if h.strip())

# Formato de cada dashboard em dados/dashboards.json:
# {"nome": "...", "url": "...", "emoji": "📊", "data": "AAAA-MM-DD"}
# "emoji" e "data" são opcionais. Vê o dashboards.exemplo.json.

STYLE = """
QWidget#MainWindow { background-color: #f0f2f5; }
QScrollArea { border: none; background-color: transparent; }
QWidget#ScrollContent { background-color: transparent; }
QLabel#Title { font-size: 18px; font-weight: 800; color: #1a1a1a; }
QLabel#HistoryTitle { font-size: 12px; font-weight: 700; color: #555; padding: 4px 2px; }
QPushButton#AppCard { background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 12px; }
QPushButton#AppCard:hover { border: 2px solid #0056b3; }
QLabel#CardText { font-size: 13px; font-weight: 700; color: #2d3436; }
QLabel#CardIcon { font-size: 36px; }
QWidget#StatusBar { background-color: #0056b3; min-height: 10px; max-height: 10px; }
QFrame#ChatBox { background-color: #ffffff; border-radius: 15px; border: 1px solid #dcdcdc; }
QWidget#ChatHeader { background-color: #007bff; border-top-left-radius: 14px; border-top-right-radius: 14px; }
QLabel#ChatHeaderText { color: white; font-size: 14px; font-weight: bold; }
QPushButton#BackBtn { background-color: #fff; color: #007bff; font-size: 10px; font-weight: bold;
                      border-radius: 4px; padding: 2px 6px; border: none; }
QLabel#BotBubble { background-color: #f0f0f0; border-radius: 10px; padding: 10px; color: #333; font-size: 12px; }
QPushButton#ChatOption { background-color: #fff; border: 1px solid #dee2e6; border-radius: 8px;
                         padding: 10px; text-align: left; font-size: 12px; color: #212529; }
QPushButton#ChatOption:hover { background-color: #f8f9fa; border-color: #007bff; }
QLineEdit, QTextEdit { background-color: #ffffff; color: #000000; border: 1px solid #ddd;
                       border-radius: 8px; padding: 5px; font-size: 11px; }
QLineEdit { padding: 2px 6px; }
"""


def utilizador_atual():
    try:
        return getpass.getuser()
    except Exception:
        return ""


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 520)
        self.opcao = ""   # "Melhoria" ou "Relatar Erro"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        conteudo = QWidget()
        main = QVBoxLayout(conteudo)
        main.setContentsMargins(30, 25, 30, 25)
        main.setSpacing(20)

        titulo = QLabel(APP_NAME)
        titulo.setObjectName("Title")
        main.addWidget(titulo)

        # cards dos dashboards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area = QWidget()
        area.setObjectName("ScrollContent")
        self.scroll.setWidget(area)
        self.grid = QGridLayout(area)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        try:
            dashboards = ler_json(FICHEIRO_DASHBOARDS, [])
            erro_dashboards = ""
        except (FicheiroCorrompido, OSError) as erro:
            dashboards = []
            erro_dashboards = f"\nErro ao ler o ficheiro: {erro}"
        # ignora entradas sem nome ou com url inválido (só https)
        dashboards = filtrar_dashboards(dashboards, HOSTS_PERMITIDOS)

        if not dashboards:
            aviso = QLabel("Nenhum dashboard configurado.\n"
                           "Adiciona-os em dados/dashboards.json" + erro_dashboards)
            aviso.setWordWrap(True)
            aviso.setStyleSheet("color:#555; font-size:13px;")
            self.grid.addWidget(aviso, 0, 0)

        for i, d in enumerate(dashboards):
            self.grid.addWidget(self.criar_card(d), i // 3, i % 3)

        # painel da direita com o feedback já enviado
        self.painel = QScrollArea()
        self.painel.setFixedWidth(220)
        self.painel.setWidgetResizable(True)
        self.painel.setStyleSheet("border-left:1px solid #ddd; background-color:#f8f8f8;")
        lista = QWidget()
        self.lista_layout = QVBoxLayout(lista)
        self.lista_layout.setAlignment(Qt.AlignTop)
        t = QLabel("Feedback enviado")
        t.setObjectName("HistoryTitle")
        self.lista_layout.addWidget(t)
        self.painel.setWidget(lista)

        linha = QWidget()
        ll = QHBoxLayout(linha)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        ll.addWidget(self.scroll, 1)
        ll.addWidget(self.painel)
        main.addWidget(linha)

        outer.addWidget(conteudo)
        barra = QWidget()
        barra.setObjectName("StatusBar")
        outer.addWidget(barra)

        self.montar_chat()

        # feedback que já estava guardado
        try:
            guardados = ler_json(FICHEIRO_FEEDBACK, [])
            if not isinstance(guardados, list):
                raise FicheiroCorrompido("esperava-se uma lista")
        except (FicheiroCorrompido, OSError) as erro:
            guardados = []
            QMessageBox.warning(self, "Aviso",
                                f"Não foi possível ler o feedback guardado:\n{erro}\n\n"
                                "O ficheiro não será alterado.")
        for item in guardados:
            if isinstance(item, dict):
                self.mostrar_feedback(item)

    # ---------- cards ----------
    def criar_card(self, d):
        btn = QPushButton()
        btn.setObjectName("AppCard")
        btn.setFixedSize(180, 160)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(partial(webbrowser.open, d["url"]))
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.setSpacing(2)

        emoji = QLabel(str(d.get("emoji") or "📊"))
        emoji.setObjectName("CardIcon")
        emoji.setAlignment(Qt.AlignCenter)
        nome = QLabel(str(d["nome"]))
        nome.setObjectName("CardText")
        nome.setWordWrap(True)
        btn.setToolTip(d["url"])
        nome.setAlignment(Qt.AlignCenter)

        data = QLabel()
        try:
            data.setText(datetime.fromisoformat(d["data"]).strftime("%d/%m/%Y"))
        except (KeyError, ValueError, TypeError):
            pass  # sem data (ou mal escrita), fica vazio
        data.setAlignment(Qt.AlignCenter)
        data.setStyleSheet("font-size:10px; color:#555;")

        for w in (emoji, nome, data):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(w)
        return btn

    # ---------- chat ----------
    def montar_chat(self):
        self.chat_btn = QPushButton("🤖", self)
        self.chat_btn.setFixedSize(50, 50)
        self.chat_btn.setCursor(Qt.PointingHandCursor)
        self.chat_btn.setStyleSheet(
            "QPushButton{border-radius:25px;background-color:#007bff;color:white;font-size:20px;border:none;}"
            "QPushButton:hover{background-color:#0056b3;}")
        self.chat_btn.clicked.connect(self.abrir_fechar_chat)

        self.chat_box = QFrame(self)
        self.chat_box.setObjectName("ChatBox")
        self.chat_box.setFixedSize(290, 300)
        self.chat_box.hide()
        v = QVBoxLayout(self.chat_box)
        v.setContentsMargins(0, 0, 0, 10)
        v.setSpacing(0)

        cabecalho = QWidget()
        cabecalho.setObjectName("ChatHeader")
        cabecalho.setFixedHeight(50)
        h = QHBoxLayout(cabecalho)
        h.setContentsMargins(10, 0, 10, 0)
        self.btn_voltar = QPushButton("VOLTAR")
        self.btn_voltar.setObjectName("BackBtn")
        self.btn_voltar.clicked.connect(self.menu_inicial)
        self.btn_voltar.hide()
        nome_chat = QLabel("Assistente")
        nome_chat.setObjectName("ChatHeaderText")
        h.addWidget(self.btn_voltar)
        h.addStretch()
        h.addWidget(nome_chat)
        h.addStretch()
        v.addWidget(cabecalho)

        corpo = QWidget()
        self.corpo = QVBoxLayout(corpo)
        self.corpo.setContentsMargins(15, 15, 15, 10)
        self.corpo.setSpacing(8)

        self.msg = QLabel("Olá 👋 Como posso ajudar?")
        self.msg.setObjectName("BotBubble")
        self.msg.setWordWrap(True)
        self.corpo.addWidget(self.msg)

        self.btn_melhoria = QPushButton("📝 Sugestão de Melhoria")
        self.btn_melhoria.setObjectName("ChatOption")
        self.btn_melhoria.clicked.connect(lambda: self.escolher("Melhoria"))
        self.btn_erro = QPushButton("⚠️ Relatar Erro")
        self.btn_erro.setObjectName("ChatOption")
        self.btn_erro.clicked.connect(lambda: self.escolher("Relatar Erro"))
        self.corpo.addWidget(self.btn_melhoria)
        self.corpo.addWidget(self.btn_erro)

        self.campo_email = QLineEdit()
        self.campo_email.setPlaceholderText("O seu email")
        self.campo_email.setFixedHeight(28)
        self.campo_texto = QTextEdit()
        self.campo_texto.setPlaceholderText("Escreva os detalhes aqui...")
        self.campo_texto.setFixedHeight(60)
        self.btn_enviar = QPushButton("Enviar Mensagem")
        self.btn_enviar.setFixedHeight(30)
        self.btn_enviar.setStyleSheet("background-color:#007bff;color:white;border-radius:6px;font-weight:bold;font-size:11px;")
        self.btn_enviar.clicked.connect(self.enviar_feedback)
        for w in (self.campo_email, self.campo_texto, self.btn_enviar):
            w.hide()
            self.corpo.addWidget(w)
        self.corpo.addStretch()
        v.addWidget(corpo)

        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(15)
        sombra.setColor(QColor(0, 0, 0, 50))
        sombra.setYOffset(4)
        self.chat_box.setGraphicsEffect(sombra)
        self.posicionar_chat()

    def abrir_fechar_chat(self):
        if self.chat_box.isVisible():
            self.chat_box.hide()
        else:
            self.menu_inicial()
            self.chat_box.show()

    def menu_inicial(self):
        self.btn_voltar.hide()
        for w in (self.campo_email, self.campo_texto, self.btn_enviar):
            w.hide()
        self.campo_email.clear()
        self.campo_texto.clear()
        self.btn_melhoria.show()
        self.btn_erro.show()
        self.msg.setText("Olá 👋 Como posso ajudar?")
        self.chat_box.setFixedHeight(280)
        self.posicionar_chat()

    def escolher(self, opcao):
        self.opcao = opcao
        self.btn_voltar.show()
        self.btn_melhoria.hide()
        self.btn_erro.hide()
        self.msg.setText(f"Selecionou: {opcao}\nDescreva abaixo:")
        for w in (self.campo_email, self.campo_texto, self.btn_enviar):
            w.show()
        self.chat_box.setFixedHeight(360)
        self.posicionar_chat()

    def enviar_feedback(self):
        texto = self.campo_texto.toPlainText().strip()
        email = self.campo_email.text().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Escreva uma mensagem antes de enviar.")
            return
        if not email_valido(email):
            QMessageBox.warning(self, "Aviso", "Indique um email válido.")
            return

        agora = datetime.now()
        item = {
            "id": agora.isoformat(timespec="microseconds") + "-" + str(os.getpid()),
            "tipo": self.opcao,
            "texto": texto,
            "email": email,
            "utilizador": utilizador_atual(),
            "data": agora.strftime("%d/%m/%Y"),
        }
        try:
            # lê, acrescenta e grava dentro de um bloqueio (ver armazenamento.py)
            alterar_lista(FICHEIRO_FEEDBACK, lambda todos: todos + [item])
        except (OSError, TimeoutError, FicheiroCorrompido) as erro:
            QMessageBox.critical(self, "Erro", f"Não foi possível guardar o feedback:\n{erro}")
            return

        self.mostrar_feedback(item)
        QMessageBox.information(self, "Sucesso", "Feedback registado!")
        self.chat_box.hide()

    # ---------- feedback ----------
    def mostrar_feedback(self, item):
        caixa = QWidget()
        h = QHBoxLayout(caixa)
        h.setContentsMargins(0, 0, 0, 0)

        texto = html.escape(item.get("texto", ""))
        label = QLabel(
            f"<span style='color:#f1c40f;font-size:14px;'>●</span> {html.escape(item.get('tipo', ''))}<br>"
            f"{item.get('data', '')}<br>{texto}")
        label.setWordWrap(True)
        label.setStyleSheet("background:#fff;color:#000;border:1px solid #ddd;border-radius:6px;padding:5px;font-size:11px;")

        lixo = QPushButton("🗑")
        lixo.setFixedSize(24, 24)
        lixo.setCursor(Qt.PointingHandCursor)
        lixo.clicked.connect(partial(self.apagar_feedback, item, caixa))

        h.addWidget(label, 1)
        h.addWidget(lixo, 0, Qt.AlignTop)
        self.lista_layout.addWidget(caixa)

    def apagar_feedback(self, item, caixa):
        # só apaga quem enviou: confere o utilizador do Windows/sistema. Em
        # feedback antigo (sem "utilizador") pede o email, como antes.
        # Nota: continua a ser uma verificação no cliente, não é segurança.
        autor = item.get("utilizador")
        if autor:
            if autor != utilizador_atual():
                QMessageBox.warning(self, "Erro", "Só quem enviou o feedback o pode apagar.")
                return
        else:
            email, ok = QInputDialog.getText(self, "Confirmar exclusão", "Digite o seu email para confirmar:")
            if not ok:
                return
            if email.strip().lower() != str(item.get("email", "")).strip().lower():
                QMessageBox.warning(self, "Erro", "Email não confere! Não é possível apagar este feedback.")
                return

        try:
            alterar_lista(FICHEIRO_FEEDBACK,
                          lambda todos: [f for f in todos
                                         if not (isinstance(f, dict) and f.get("id") == item.get("id"))])
        except (OSError, TimeoutError, FicheiroCorrompido) as erro:
            QMessageBox.critical(self, "Erro", f"Não foi possível apagar:\n{erro}")
            return

        self.lista_layout.removeWidget(caixa)
        caixa.deleteLater()
        QMessageBox.information(self, "Sucesso", "Feedback apagado com sucesso!")

    # ---------- posição do chat ----------
    def posicionar_chat(self):
        margem = 15
        self.chat_btn.move(self.width() - self.chat_btn.width() - margem,
                           self.height() - self.chat_btn.height() - margem - 10)
        self.chat_box.move(self.width() - self.chat_box.width() - margem,
                           self.chat_btn.y() - self.chat_box.height() - 8)

    def resizeEvent(self, evento):
        self.posicionar_chat()
        super().resizeEvent(evento)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = Launcher()
    janela.setStyleSheet(STYLE)
    janela.show()
    sys.exit(app.exec())