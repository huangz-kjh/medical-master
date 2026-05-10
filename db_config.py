# 数据库配置文件

DB_CONFIG = {
    'local': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'app',
    },
    'remote': {
        'host': 'dbconn.sealosbja.site',
        'port': 42757,
        'user': 'root',
        'password': '4scc7fn5',
        'database': 'app',
    }
}

def get_sqlalchemy_uri(db_type='local'):
    conf = DB_CONFIG[db_type]
    return f"mysql+pymysql://{conf['user']}:{conf['password']}@{conf['host']}:{conf['port']}/{conf['database']}"
