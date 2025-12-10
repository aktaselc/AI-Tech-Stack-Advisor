#!/usr/bin/env python3
"""
Bulwise Analytics Viewer
Simple script to view your user query analytics
"""

import sqlite3
from datetime import datetime
from collections import Counter

def view_analytics():
    """Display analytics summary from bulwise_analytics.db"""
    
    try:
        conn = sqlite3.connect('bulwise_analytics.db')
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("BULWISE ANALYTICS DASHBOARD")
        print("="*60 + "\n")
        
        # Total queries
        cursor.execute("SELECT COUNT(*) FROM queries")
        total = cursor.fetchone()[0]
        print(f"📊 Total Queries: {total}")
        
        # Total users and return users
        cursor.execute("SELECT COUNT(DISTINCT user_session_id) FROM queries")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT user_session_id) FROM queries WHERE is_return_user = 1")
        return_users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM queries WHERE is_return_user = 1")
        return_user_queries = cursor.fetchone()[0]
        
        print(f"👥 Total Users: {total_users}")
        print(f"🔄 Return Users: {return_users_count} ({(return_users_count/total_users*100) if total_users > 0 else 0:.1f}%)")
        print(f"🔄 Queries from Return Users: {return_user_queries} ({(return_user_queries/total*100) if total > 0 else 0:.1f}%)")
        
        # Average days between visits
        cursor.execute("SELECT AVG(days_since_last_visit) FROM queries WHERE is_return_user = 1 AND days_since_last_visit > 0")
        avg_days = cursor.fetchone()[0]
        if avg_days:
            print(f"📅 Avg Days Between Return Visits: {avg_days:.1f} days\n")
        else:
            print()
        
        if total == 0:
            print("No queries logged yet. Start using your app to collect data!")
            conn.close()
            return
        
        # Top categories
        print("🏆 TOP CATEGORIES")
        print("-" * 60)
        cursor.execute("""
            SELECT detected_category, COUNT(*) as count 
            FROM queries 
            WHERE detected_category != ''
            GROUP BY detected_category 
            ORDER BY count DESC 
            LIMIT 10
        """)
        
        categories = cursor.fetchall()
        for category, count in categories:
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            print(f"{category:20} {count:3} queries {bar} {percentage:.1f}%")
        
        print()
        
        # Team sizes
        print("👥 TEAM SIZE DISTRIBUTION")
        print("-" * 60)
        cursor.execute("""
            SELECT team_size, COUNT(*) as count 
            FROM queries 
            GROUP BY team_size 
            ORDER BY count DESC
        """)
        
        for team_size, count in cursor.fetchall():
            percentage = (count / total) * 100
            print(f"{team_size:15} {count:3} queries ({percentage:.1f}%)")
        
        print()
        
        # Budget mentions
        cursor.execute("SELECT COUNT(*) FROM queries WHERE budget_mentioned = 1")
        budget_count = cursor.fetchone()[0]
        budget_percentage = (budget_count / total) * 100
        print(f"💰 Budget Mentioned: {budget_count} queries ({budget_percentage:.1f}%)")
        
        # Rate limit hits
        cursor.execute("SELECT COUNT(*) FROM queries WHERE rate_limit_hit = 1")
        limit_count = cursor.fetchone()[0]
        print(f"🚫 Hit Rate Limit: {limit_count} queries ({(limit_count/total)*100:.1f}%)")
        
        print()
        
        # User engagement metrics
        print("📈 USER ENGAGEMENT")
        print("-" * 60)
        cursor.execute("SELECT AVG(visit_count) FROM queries")
        avg_visits = cursor.fetchone()[0]
        print(f"Average Visit Count: {avg_visits:.1f}")
        
        cursor.execute("SELECT MAX(visit_count) FROM queries")
        max_visits = cursor.fetchone()[0]
        print(f"Most Engaged User: {max_visits} visits")
        
        # Visit count distribution
        cursor.execute("""
            SELECT visit_count, COUNT(DISTINCT user_session_id) as user_count
            FROM queries
            GROUP BY visit_count
            ORDER BY visit_count
            LIMIT 5
        """)
        print("\nVisit Distribution:")
        for visits, users in cursor.fetchall():
            print(f"  {visits} visit(s): {users} users")
        
        print()
        
        # Recent queries
        print("🕐 RECENT QUERIES (Last 10)")
        print("-" * 60)
        cursor.execute("""
            SELECT timestamp, detected_category, query_length, user_query, is_return_user, visit_count 
            FROM queries 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        for timestamp, category, length, query, is_return, visit_count in cursor.fetchall():
            dt = datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M")
            query_preview = query[:70] + "..." if len(query) > 70 else query
            user_type = f"Return user (visit #{visit_count})" if is_return else "New user"
            print(f"\n{formatted_time} | {category:12} | {length:3} chars | {user_type}")
            print(f"  "{query_preview}"")
        
        print("\n" + "="*60)
        
        # Query length stats
        cursor.execute("SELECT AVG(query_length), MIN(query_length), MAX(query_length) FROM queries")
        avg_len, min_len, max_len = cursor.fetchone()
        print(f"\n📏 Query Length: Avg={avg_len:.0f} | Min={min_len} | Max={max_len} chars")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        print("\nMake sure bulwise_analytics.db exists in the current directory.")
    except Exception as e:
        print(f"❌ Error: {e}")

def export_to_csv():
    """Export all analytics data to CSV"""
    import csv
    
    try:
        conn = sqlite3.connect('bulwise_analytics.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM queries ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(queries)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Write to CSV
        filename = f"bulwise_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        print(f"✅ Exported {len(rows)} queries to {filename}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Export error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        print("\n📥 Exporting analytics to CSV...")
        export_to_csv()
    else:
        view_analytics()
        print("\n💡 Tip: Run 'python view_analytics.py --export' to export data to CSV\n")
