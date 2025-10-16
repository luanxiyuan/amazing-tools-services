from common_tools import file_tools
from consts.sys_constants import SysConstants

# The function to get all the supported database types, file from sql_generator_config.json
def get_supported_database_types():
    sql_generator_config = file_tools.load_module_config_file(SysConstants.SQL_GENERATOR.value)
    database_types = sql_generator_config['database_types']
    return database_types



# The function to check the DB connection
def check_db_connection(db_type, db_host, db_port, db_name, db_user, db_password):
    connection = build_connection(db_type, db_host, db_port, db_name, db_user, db_password)
    if connection:
        close_connection(connection)
        return {"status": SysConstants.STATUS_SUCCESS.value, "message": ""}
    else:
        return { "status": SysConstants.STATUS_FAILED.value, "message": "Failed to connect to the database" }


# The function to build the connection with a database, support mysql, oracle, posgresql, sqlserver
def build_connection(db_type, db_host, db_port, db_name, db_user, db_password):
    db_port = int(db_port)
    connection = None
    try:
        if db_type == "mysql":
            import pymysql
            connection = pymysql.Connect(
                host=db_host,
                port=db_port,
                db=db_name,
                user=db_user,
                passwd=db_password,
                charset="utf8mb4"
            )
        elif db_type == "oracle":
            import cx_Oracle
            dsn = cx_Oracle.makedsn(db_host, db_port, service_name=db_name)
            connection = cx_Oracle.connect(user=db_user, password=db_password, dsn=dsn)
        elif db_type == "postgresql":
            import psycopg2
            connection = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
        elif db_type == "sqlserver":
            import pyodbc
            conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_host},{db_port};DATABASE={db_name};UID={db_user};PWD={db_password}'
            connection = pyodbc.connect(conn_str)
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    return connection


# The function to close the connection with a database
def close_connection(connection):
    try:
        if connection:
            connection.close()
    except Exception as e:
        print(f"Error closing the connection: {e}")


# The function to get the database version
def get_database_version(connection):
    version = ""
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type == "pymysql":
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        elif db_type == "cx_Oracle":
            cursor.execute("SELECT * FROM v$version")
            version = cursor.fetchone()[0]
        elif db_type == "psycopg2":
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
        elif db_type == "pyodbc":
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error fetching database version: {e}")
    return version


# The function to get the table list from a database
def get_table_list(connection):
    tables = []
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type == "pymysql":
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
        elif db_type == "cx_Oracle":
            cursor.execute("SELECT table_name FROM user_tables")
            tables = [row[0] for row in cursor.fetchall()]
        elif db_type == "psycopg2":
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = [row[0] for row in cursor.fetchall()]
        elif db_type == "pyodbc":
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'")
            tables = [row[0] for row in cursor.fetchall()]
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error fetching table list: {e}")
    return tables


# The function to get all the column names and corresponding comments from a table
def get_table_column_comments(connection, table_name):
    column_comments = []
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type == "pymysql":
            cursor.execute(f"SHOW FULL COLUMNS FROM {table_name}")
            column_comments = [{
                "Column_Name": row[0],
                "Comment": row[8]
            } for row in cursor.fetchall()]
        elif db_type == "cx_Oracle":
            cursor.execute(f"""
                SELECT column_name, comments
                FROM user_tab_columns
                JOIN user_col_comments USING (table_name, column_name)
                WHERE table_name = '{table_name.upper()}'
            """)
            column_comments = [{
                "Column_Name": row[0],
                "Comment": row[1]
            } for row in cursor.fetchall()]
        elif db_type == "psycopg2":
            cursor.execute(f"""
                SELECT column_name, column_comment
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                """)
            column_comments = [{
                "Column_Name": row[0],
                "Comment": row[1]
            } for row in cursor.fetchall()]
        elif db_type == "pyodbc":
            cursor.execute(f"""
                SELECT COLUMN_NAME, COLUMN_DESCRIPTION
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
                """)
            column_comments = [{
                "Column_Name": row[0],
                "Comment": row[1]
            } for row in cursor.fetchall()]
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error fetching column comments: {e}")
    return column_comments


# The function to get all the columns related information (column name, type, if null, key type, default value, comments) from a table
def get_table_columns(connection, table_name):
    columns = []
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type == "pymysql":
            cursor.execute(f"SHOW FULL COLUMNS FROM {table_name}")
            columns = [{
                "Field": row[0],
                "Type": row[1],
                "Null": row[3],
                "Key": row[4],
                "Default": row[5],
                "Comment": row[8]
            } for row in cursor.fetchall()]
        elif db_type == "cx_Oracle":
            cursor.execute(f"""
                SELECT column_name, data_type, nullable, data_default
                FROM user_tab_columns
                WHERE table_name = '{table_name.upper()}'
            """)
            columns = [{
                "Column_Name": row[0],
                "Data_Type": row[1],
                "Nullable": row[2],
                "Data_Default": row[3]
            } for row in cursor.fetchall()]
        elif db_type == "psycopg2":
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """)
            columns = [{
                "Column_Name": row[0],
                "Data_Type": row[1],
                "Is_Nullable": row[2],
                "Column_Default": row[3]
            } for row in cursor.fetchall()]
        elif db_type == "pyodbc":
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
            """)
            columns = [{
                "Column_Name": row[0],
                "Data_Type": row[1],
                "Is_Nullable": row[2],
                "Column_Default": row[3]
            } for row in cursor.fetchall()]
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error fetching columns for table {table_name}: {e}")
    return columns


# The function to get all the foreign key related information (column name, referenced table, referenced column) from a table
def get_table_foreign_keys(connection, table_name):
    foreign_keys = []
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type == "pymysql":
            cursor.execute(f"""
                SELECT 
                    CONSTRAINT_NAME, 
                    COLUMN_NAME, 
                    REFERENCED_TABLE_NAME, 
                    REFERENCED_COLUMN_NAME 
                FROM 
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE 
                    TABLE_NAME = '{table_name}' 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            foreign_keys = [{
                "Constraint_Name": row[0],
                "Column_Name": row[1],
                "Referenced_Table_Name": row[2],
                "Referenced_Column_Name": row[3]
            } for row in cursor.fetchall()]
        elif db_type == "cx_Oracle":
            cursor.execute(f"""
                SELECT 
                    a.constraint_name, 
                    a.column_name, 
                    b.table_name referenced_table_name, 
                    b.column_name referenced_column_name 
                FROM 
                    all_cons_columns a, 
                    all_constraints b 
                WHERE 
                    a.constraint_name = b.constraint_name 
                    AND a.table_name = '{table_name}' 
                    AND b.constraint_type = 'R';
            """)
            foreign_keys = [{
                "Constraint_Name": row[0],
                "Column_Name": row[1],
                "Referenced_Table_Name": row[2],
                "Referenced_Column_Name": row[3]
            } for row in cursor.fetchall()]
        elif db_type == "psycopg2":
            cursor.execute(f"""
                SELECT 
                    conname AS constraint_name, 
                    attname AS column_name, 
                    confrelid::regclass AS referenced_table_name, 
                    confrelatt AS referenced_column_name 
                FROM 
                    pg_attribute 
                JOIN 
                    pg_constraint ON pg_attribute.attnum = pg_constraint.confkey[1] 
                WHERE 
                    pg_attribute.attnum > 0 AND pg_attribute.attnum = ANY(pg_constraint.confkey) AND pg_constraint.contype = 'f' AND pg_attribute.attnum = ANY(pg_constraint.confkey) AND pg_constraint.contype = 'f' AND pg_constraint.conrelid = '{table_name}'::regclass;
                           """)
            foreign_keys = [{
                "Constraint_Name": row[0],
                "Column_Name": row[1],
                "Referenced_Table_Name": row[2],
                "Referenced_Column_Name": row[3]
            } for row in cursor.fetchall()]
        elif db_type == "pyodbc":
            cursor.execute(f"""
                SELECT 
                    fk.name AS constraint_name, 
                    fk.cols.name AS column_name, 
                    fk.reftab.name AS referenced_table_name, 
                    fk.reftab.cols.name AS referenced_column_name 
                FROM 
                    sys.foreign_keys fk 
                JOIN 
                    sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                JOIN 
                    sys.columns fk_cols ON fkc.parent_object_id = fk_cols.object_id AND fkc.parent_column_id = fk_cols.column_id
                JOIN 
                    sys.columns fk_reftab_cols ON fkc.referenced_object_id = fk_reftab_cols.object_id AND fkc.referenced_column_id = fk_reftab_cols.column_id
                JOIN 
                    sys.tables fk_tab ON fk_cols.object_id = fk_tab.object_id
                JOIN 
                    sys.tables fk_reftab ON fk_reftab_cols.object_id = fk_reftab.object_id;
                WHERE 
                    fk_tab.name = '{table_name}';
            """)
            foreign_keys = [{
                "Constraint_Name": row[0],
                "Column_Name": row[1],
                "Referenced_Table_Name": row[2],
                "Referenced_Column_Name": row[3]
            } for row in cursor.fetchall()]
        else:
            raise Exception(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error occurred while getting foreign keys for table {table_name}: {str(e)}")
    finally:
        cursor.close()
    return foreign_keys


# The function to get all the indexes related information (Cardinality, Non_unique, Seq_in_index, Column_name, Collation, Null, Index_type, Comment, Index_comment) of a table
def get_indexes(connection, table_name):
    indexes = []
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type == "pymysql":
            cursor.execute(f"SHOW INDEXES FROM {table_name}")
            indexes = [{
                "Non_unique": row[1],
                "Key_name": row[2],
                "Seq_in_index": row[3],
                "Column_name": row[4],
                "Collation": row[5],
                "Cardinality": row[6],
                "Null": row[9],
                "Index_type": row[10],
                "Comment": row[11],
                "Index_comment": row[12]
                } for row in cursor.fetchall()]
        elif db_type == "cx_Oracle":
            cursor.execute(f"""
                SELECT 
                    index_name, 
                    column_name, 
                    column_position, 
                    descending, 
                    num_rows AS cardinality, 
                    uniqueness, 
                    index_type, 
                    index_comment 
                FROM 
                    all_ind_columns 
                JOIN 
                    all_indexes ON all_ind_columns.index_name = all_indexes.index_name 
                WHERE 
                    all_ind_columns.table_name = '{table_name}';
                    """)
            indexes = [{
                "Non_unique": row[4],
                "Key_name": row[0],
                "Seq_in_index": row[2],
                "Column_name": row[1],
                "Collation": row[3],
                "Cardinality": row[5],
                "Null": None,
                "Index_type": row[6],
                "Comment": None,
                "Index_comment": row[7]
                } for row in cursor.fetchall()]
        elif db_type == "psycopg2":
            cursor.execute(f"""
                SELECT 
                    indexname AS key_name, 
                    attname AS column_name, 
                    attnum AS seq_in_index, 
                    CASE WHEN indisunique THEN 0 ELSE 1 END AS non_unique, 
                    pg_stat_user_indexes.idx_scan AS cardinality, 
                    CASE WHEN indisprimary THEN 'PRIMARY' WHEN indisunique THEN 'UNIQUE' ELSE 'INDEX' END AS index_type, 
                    indexdef AS index_comment 
                FROM 
                    pg_indexes 
                JOIN 
                    pg_attribute ON pg_indexes.tablename = pg_attribute.attrelid::regclass::text AND pg_indexes.indexdef LIKE '%' || pg_attribute.attname || '%'
                    JOIN pg_stat_user_indexes ON pg_indexes.indexname = pg_stat_user_indexes.indexrelid::regclass::text 
                WHERE 
                    pg_indexes.tablename = '{table_name}';
                    """)
            indexes = [{
            "Non_unique": row[3],
            "Key_name": row[0],
            "Seq_in_index": row[2],
            "Column_name": row[1],
            "Collation": None,
            "Cardinality": row[4],
            "Null": None,
            "Index_type": row[5],
            "Comment": None,
            "Index_comment": row[6]
            } for row in cursor.fetchall()]
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error occurred while getting indexes for table {table_name}: {str(e)}")
    finally:
        cursor.close()
        return indexes


# The function to get the total number of rows in a table
def get_table_row_count(connection, table_name):
    row_count = 0
    try:
        cursor = connection.cursor()
        db_type = connection.__class__.__module__.split('.')[0]
        if db_type in ["pymysql", "cx_Oracle", "psycopg2", "pyodbc"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
        else:
            print(f"Unsupported database type: {db_type}")
    except Exception as e:
        print(f"Error fetching row count for table {table_name}: {e}")
    return row_count


# The function to generate the output content based on database information, table information and business requirements
def generate_db_prompt(connection, table_names, operation_type, business_requirement, existing_sql):
    """
    生成输出内容，包含数据库信息、表信息和业务需求
    
    Args:
        db_type: 数据库类型 (MySQL, PostgreSQL, Oracle, SQL Server)
        db_host: 数据库主机地址
        db_port: 数据库端口
        db_name: 数据库名称
        db_user: 数据库用户名
        db_password: 数据库密码
        table_names: 需要查询的表名列表
        business_requirements: 业务需求字典，包含查询目标、过滤条件、排序、分页等信息
        
    Returns:
        str: 生成的输出内容
    """
    output = []
    
    # 获取数据库信息
    db_version = get_database_version(connection)
    db_module = connection.__class__.__module__.split('.')[0]
    
    # 提取数据库类型名称
    if "pymysql" in db_module:
        db_type_name = "MySQL"
    elif "cx_Oracle" in db_module:
        db_type_name = "Oracle"
    elif "psycopg2" in db_module:
        db_type_name = "PostgreSQL"
    elif "pyodbc" in db_module:
        db_type_name = "SQL Server"
    else:
        db_type_name = "Unknown"
    # prompt system_role defination
    output.append(f"请作为专业的数据库专家，请基于以下的信息和要求给出一个最优的方案。")
    # 添加数据库信息
    output.append(f"- 数据库信息：{db_type_name} {db_version}")
    output.append("- 表信息：")
    
    # 获取每个表的详细信息
    for table_name in table_names:
        output.append(f"  - 表名：{table_name}:")

        # 获取表数据量
        row_count = get_table_row_count(connection, table_name)
        # 将行数转换为万/百万单位显示
        if row_count >= 1000000:
            display_count = f"{row_count / 1000000:.1f}百万行"
        elif row_count >= 10000:
            display_count = f"{row_count / 10000:.1f}万行"
        else:
            display_count = f"{row_count}行"
        output.append(f"    - 表数据量：{display_count}")
        
        # 获取表字段信息 - 把能查到的所有信息都输出
        columns = get_table_columns(connection, table_name)
        output.append("    - 表字段信息：")
        for col in columns:
            col_name = col.get('Column_Name', col.get('Field', ''))
            col_type = col.get('Data_Type', col.get('Type', ''))
            is_nullable = col.get('Is_Nullable', col.get('Null', ''))
            col_default = col.get('Column_Default', col.get('Default', ''))
            col_key = col.get('Key', '')
            col_comment = col.get('Comment', '')
            
            nullable_text = "可为空" if is_nullable in ['YES', 'Y', True] else "不可为空"
            default_text = f", 默认值: {col_default}" if col_default else ""
            key_text = f", 键类型: {col_key}" if col_key else ""
            comment_text = f", 注释: {col_comment}" if col_comment else ""
            
            output.append(f"      - {col_name}: {col_type} ({nullable_text}{default_text}{key_text}{comment_text})")

        # 获取外键信息 - 把能查到的所有信息都输出
        foreign_keys = get_table_foreign_keys(connection, table_name)
        output.append("    - 外键信息：")
        if foreign_keys:
            for fk in foreign_keys:
                constraint_name = fk.get('Constraint_Name', '')
                column_name = fk.get('Column_Name', '')
                ref_table = fk.get('Referenced_Table_Name', '')
                ref_column = fk.get('Referenced_Column_Name', '')
                output.append(f"      - {constraint_name}: {column_name} -> {ref_table}.{ref_column}")
        else:
            output.append("      - 无外键信息")
        
        # 获取索引信息 - 把能查到的所有信息都输出
        indexes = get_indexes(connection, table_name)
        output.append("    - 索引信息：")
        if indexes:
            for idx in indexes:
                idx_name = idx.get('Key_name', '')
                unique_text = "唯一" if idx.get('Non_unique', 1) == 0 else "非唯一"
                idx_type = idx.get('Index_type', '')
                columns = idx.get('Column_name', '')
                collation = idx.get('Collation', '')
                cardinality = idx.get('Cardinality', 0)
                comment = idx.get('Comment', '')
                index_comment = idx.get('Index_comment', '')
                
                collation_text = f", 排序规则: {collation}" if collation else ""
                cardinality_text = f", 基数: {cardinality}" if cardinality else ""
                comment_text = f", 注释: {comment}" if comment else ""
                index_comment_text = f", 索引注释: {index_comment}" if index_comment else ""
                
                output.append(f"      - {idx_name} ({unique_text}): {columns} ({idx_type}{collation_text}{cardinality_text}{comment_text}{index_comment_text})")
        else:
            output.append("      - 无索引信息")

    # business requirement
    # operation type
    if operation_type == "query":
        output.append(f"- 业务需求：{business_requirement}")
        output.append(f"- 查询场景：高频查询，要求极致的响应速度")
        output.append("- 基于以上现有的数据库和表信息，不改变表结构，索引等内容的前提下，直接给出一个最优的SQL语句和必要的解释")
    elif operation_type == "optimize":
        output.append("- 基于以上现有的数据库和表信息，给出优化方案，包括但不限于修改表的索引，优化现有SQL脚本等，并给出必要的解释")
        output.append("- 现有数据库SQL脚本如下：")
        output.append(existing_sql)

    close_connection(connection)

    return {
        "db_info": "\n".join(output)
    }