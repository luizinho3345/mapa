import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'chave_secreta_ceep_oficial'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configurações do Banco de Dados SQLite e Pastas
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'ceep.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_atestados')
DOCS_FOLDER = os.path.join(BASE_DIR, 'static', 'docs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCS_FOLDER'] = DOCS_FOLDER

db = SQLAlchemy(app)

# ==========================================
# MODELOS DO BANCO DE DADOS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    nome_completo = db.Column(db.String(120), nullable=False)
    cgm = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cgm_aluno = db.Column(db.String(20), nullable=False)
    nome_aluno = db.Column(db.String(120), nullable=False)
    empresa = db.Column(db.String(120), nullable=False)
    funcao = db.Column(db.String(120), nullable=False)
    carga_horaria = db.Column(db.String(50), nullable=False)
    tempo_restante = db.Column(db.String(80), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

class Atestado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cgm_aluno = db.Column(db.String(20), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Pendente')

class DeclaracaoSolicitada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_aluno = db.Column(db.String(120), nullable=False)
    cgm = db.Column(db.String(20), nullable=False)
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)

class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cgm_destinatario = db.Column(db.String(20), nullable=False)
    remetente = db.Column(db.String(80), default='Secretaria')
    titulo = db.Column(db.String(150), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    anexo_nome = db.Column(db.String(255), nullable=True)
    anexo_path = db.Column(db.String(255), nullable=True)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    lida = db.Column(db.Boolean, default=False)


# Inicialização do Banco com Cadastros de Teste
with app.app_context():
    db.create_all()

    # ALUNO 1 DE TESTE
    if not User.query.filter_by(cgm='12345678').first():
        aluno1 = User(
            username='joao.silva',
            password='123',
            nome_completo='João Silva Santos',
            cgm='12345678',
            email='joao.silva@escola.pr.gov.br'
        )
        db.session.add(aluno1)

        contrato1 = Contract(
            cgm_aluno='12345678',
            nome_aluno='João Silva Santos',
            empresa='Tech Soluções CEEP LTDA',
            funcao='Menor Aprendiz / Auxiliar de TI',
            carga_horaria='20 horas semanais',
            tempo_restante='6 Meses (Vence em 15/12/2026)'
        )
        db.session.add(contrato1)

        msg1 = Mensagem(
            cgm_destinatario='12345678',
            remetente='Secretaria',
            titulo='Bem-vindo à Secretaria Virtual',
            conteudo='Sua conta foi cadastrada com sucesso. Aqui você receberá avisos e documentos solicitados.'
        )
        db.session.add(msg1)

    # ALUNO 2 DE TESTE
    if not User.query.filter_by(cgm='87654321').first():
        aluno2 = User(
            username='maria.souza',
            password='123',
            nome_completo='Maria Oliveira Souza',
            cgm='87654321',
            email='maria.souza@escola.pr.gov.br'
        )
        db.session.add(aluno2)

        contrato2 = Contract(
            cgm_aluno='87654321',
            nome_aluno='Maria Oliveira Souza',
            empresa='Inova Marketing Eireli',
            funcao='Estagiária de Comunicação Visual',
            carga_horaria='30 horas semanais',
            tempo_restante='12 Meses (Vence em 10/06/2027)'
        )
        db.session.add(contrato2)

        msg2 = Mensagem(
            cgm_destinatario='87654321',
            remetente='Secretaria',
            titulo='Relatório do Estágio Supervisionado',
            conteudo='Lembre-se de protocolar seu relatório mensal na secretaria até o final do mês.'
        )
        db.session.add(msg2)

    db.session.commit()

# ==========================================
# ROTAS E AUTENTICAÇÃO
# ==========================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    return render_template('index.html', user=user, username=user.nome_completo, cgm=user.cgm)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username', '').strip()
        senha = request.form.get('senha', '').strip()

        if action == 'login':
            user = User.query.filter_by(username=username, password=senha).first()
            if user:
                session['user_id'] = user.id
                session['cgm'] = user.cgm
                return redirect(url_for('index'))
            else:
                flash('Nome de usuário ou senha incorretos.')
                return redirect(url_for('login'))

        elif action == 'register':
            email = request.form.get('email', '').strip()

            if User.query.filter_by(username=username).first():
                flash('Este nome de usuário já está em uso.')
                return redirect(url_for('login'))

            # Gera um CGM de 8 dígitos
            novo_cgm = str(random.randint(10000000, 99999999))
            while User.query.filter_by(cgm=novo_cgm).first():
                novo_cgm = str(random.randint(10000000, 99999999))

            novo_usuario = User(
                username=username,
                password=senha,
                nome_completo=username.title(),
                cgm=novo_cgm,
                email=email
            )
            db.session.add(novo_usuario)

            msg_boas_vindas = Mensagem(
                cgm_destinatario=novo_cgm,
                remetente='Secretaria',
                titulo='Bem-vindo ao CEEP Mapa!',
                conteudo=f'Sua conta foi criada com sucesso! O seu número de CGM gerado é: {novo_cgm}.'
            )
            db.session.add(msg_boas_vindas)
            db.session.commit()

            flash('Conta criada com sucesso! Faça login para continuar.')
            return redirect(url_for('login'))

    if 'user_id' in session:
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# APIS DA APLICAÇÃO
# ==========================================

@app.route('/api/trocar-aluno/<cgm>')
def trocar_aluno(cgm):
    user = User.query.filter_by(cgm=cgm).first()
    if user:
        session['user_id'] = user.id
        session['cgm'] = user.cgm
        return jsonify({
            'sucesso': True,
            'nome_completo': user.nome_completo,
            'cgm': user.cgm
        })
    return jsonify({'sucesso': False, 'mensagem': 'Aluno não encontrado.'})

@app.route('/api/consultar-contrato', methods=['POST'])
def consultar_contrato():
    data = request.get_json() or {}
    nome = data.get('nome', '').strip()
    
    contrato = Contract.query.filter(Contract.nome_aluno.ilike(f"%{nome}%")).first()

    if contrato:
        return jsonify({
            'sucesso': True,
            'empresa': contrato.empresa,
            'funcao': contrato.funcao,
            'carga_horaria': contrato.carga_horaria,
            'tempo_restante': contrato.tempo_restante
        })
    return jsonify({'sucesso': False, 'mensagem': 'Nenhum contrato ativo encontrado para este nome.'})

@app.route('/api/protocolar-atestado', methods=['POST'])
def protocolar_atestado():
    if 'file' not in request.files:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado.'})

    file = request.files['file']
    cgm = request.form.get('cgm', session.get('cgm', '12345678'))

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({'sucesso': False, 'mensagem': 'Por favor, envie um arquivo no formato PDF.'})

    filename = secure_filename(f"atestado_{cgm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    novo_atestado = Atestado(cgm_aluno=cgm, nome_arquivo=filename)
    db.session.add(novo_atestado)
    db.session.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Atestado protocolado com sucesso!'})

@app.route('/api/solicitar-declaracao', methods=['POST'])
def solicitar_declaracao():
    data = request.get_json() or {}
    nome = data.get('nome', '').strip()
    cgm = data.get('cgm', '').strip()

    if not nome or not cgm:
        return jsonify({'sucesso': False, 'mensagem': 'Preencha o Nome Completo e o CGM.'})

    nova_solicitacao = DeclaracaoSolicitada(nome_aluno=nome, cgm=cgm)
    db.session.add(nova_solicitacao)

    texto_mensagem = (
        "Segue a sua Declaração de Escolaridade e Frequência, conforme solicitado!\n"
        "Att, Secretaria CEEP - Centro de Educação Estadual Profissional Pedro Boarreto Neto."
    )

    nova_mensagem = Mensagem(
        cgm_destinatario=cgm,
        remetente='Secretaria',
        titulo='Declaração de Escolaridade e Frequência',
        conteudo=texto_mensagem,
        anexo_nome='Declaração_Escolaridade_TESTE.pdf',
        anexo_path='TESTE.pdf'
    )
    db.session.add(nova_mensagem)
    db.session.commit()

    return jsonify({'sucesso': True})

@app.route('/api/mensagens/<cgm>', methods=['GET'])
def obter_mensagens(cgm):
    mensagens = Mensagem.query.filter_by(cgm_destinatario=cgm).order_by(Mensagem.data_envio.desc()).all()
    resultado = []
    for msg in mensagens:
        resultado.append({
            'id': msg.id,
            'remetente': msg.remetente,
            'titulo': msg.titulo,
            'conteudo': msg.conteudo,
            'anexo_nome': msg.anexo_nome,
            'anexo_path': msg.anexo_path,
            'data': msg.data_envio.strftime('%d/%m/%Y às %H:%M'),
            'lida': msg.lida
        })
    return jsonify({'sucesso': True, 'mensagens': resultado})

@app.route('/api/mensagens/marcar-lida/<int:msg_id>', methods=['POST'])
def marcar_lida(msg_id):
    msg = Mensagem.query.get(msg_id)
    if msg:
        msg.lida = True
        db.session.commit()
        return jsonify({'sucesso': True})
    return jsonify({'sucesso': False})

@app.route('/download-doc/<filename>')
def download_doc(filename):
    return send_from_directory(app.config['DOCS_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)