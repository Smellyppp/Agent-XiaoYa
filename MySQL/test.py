import mysql.connector
from config import DB_CONFIG

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def fetch_and_print_table():
    conn = None
    cursor = None
    try:
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # 使用字典格式返回结果（字段名作为键）

        # 执行查询（注意：表名 law-1 需要用反引号 `` 包裹，因为包含特殊字符）
        query = "SELECT * FROM `catalog`"
        cursor.execute(query)

        # 获取所有行
        rows = cursor.fetchall()

        if not rows:
            print("表 `law-1` 中没有数据。")
            return

        # 打印表头（字段名）
        print("\n表 `law-1` 的内容：")
        print("-" * 50)
        if rows:
            headers = rows[0].keys()
            print("\t".join(headers))  # 用制表符分隔字段名

        # 打印每一行数据
        for row in rows:
            print("\t".join(str(row[col]) for col in headers))
        print("-" * 50)

    except mysql.connector.Error as e:
        print(f"数据库错误: {e}")
    finally:
        # 关闭游标和连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 调用函数
if __name__ == "__main__":
    fetch_and_print_table()