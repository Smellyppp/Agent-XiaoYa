import pymysql
from config import DB_CONFIG

def create_tables():
    """创建民法典数据库表结构"""
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. 创建编目表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalog (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '编目ID',
            part VARCHAR(50) NOT NULL COMMENT '编（如：第一编）',
            subpart VARCHAR(50) COMMENT '分编（如：第一分编）',
            chapter VARCHAR(50) NOT NULL COMMENT '章（如：第一章）',
            section VARCHAR(50) COMMENT '节（如：第一节）',
            start_article INT NOT NULL COMMENT '起始条目',
            end_article INT NOT NULL COMMENT '结束条目',
            UNIQUE KEY idx_hierarchy (part, subpart, chapter, section)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='民法典编目结构'
        """)
        
        # 2. 创建法律条文表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS law_articles (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '条文ID',
            catalog_id INT NOT NULL COMMENT '关联编目ID',
            article_number INT NOT NULL COMMENT '条文序号（如：1）',
            content TEXT NOT NULL COMMENT '条文内容',
            word_count INT NOT NULL COMMENT '文字数',
            CONSTRAINT fk_catalog
                FOREIGN KEY (catalog_id) 
                REFERENCES catalog(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律条文内容'
        """)
        
        # 3. 创建索引（修改处：移除IF NOT EXISTS）
        try:
            cursor.execute("CREATE INDEX idx_article_number ON law_articles(article_number)")
        except pymysql.Error as e:
            if e.args[0] != 1061:  # 1061是索引已存在的错误码
                raise
        
        try:
            cursor.execute("CREATE INDEX idx_catalog ON law_articles(catalog_id)")
        except pymysql.Error as e:
            if e.args[0] != 1061:
                raise
        
        conn.commit()
        print("成功创建数据库表结构")
        
    except pymysql.Error as e:
        print("创建表失败:", e)
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    create_tables()