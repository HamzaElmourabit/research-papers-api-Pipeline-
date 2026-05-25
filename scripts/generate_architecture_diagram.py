"""
Generate Architecture Diagram with Graphviz

Installation:
    pip install graphviz

Then download and install Graphviz from: https://graphviz.org/download/

Usage:
    python generate_architecture_diagram.py
    
Output:
    architecture_diagram.png (in docs/ folder)
"""

from graphviz import Digraph
from pathlib import Path

def generate_architecture_diagram():
    """Generate the complete ETL + ELT architecture diagram."""
    
    # Create graph
    g = Digraph('Research Papers Pipeline', format='png', 
                comment='ETL + ELT Architecture')
    
    # Graph settings
    g.attr(rankdir='TB', splines='ortho', nodesep='0.5')
    g.attr('node', shape='box', style='rounded,filled', 
           fillcolor='white', fontname='Arial', fontsize='10')
    
    # Colors
    arxiv_color = '#fff3e0'
    etl_color = '#e1f5ff'
    cassandra_color = '#fce4ec'
    elt_color = '#f3e5f5'
    output_color = '#e8f5e9'
    
    # ========== SOURCE ==========
    g.node('arxiv', '🌐 arXiv API\nResearch Papers\n500-1000 papers/day', 
           fillcolor=arxiv_color, shape='cylinder')
    
    # ========== PHASE 1: ETL (Dagster) ==========
    g.node('etl_label', 'PHASE 1: ETL\n(Dagster Orchestration)', 
           shape='note', fillcolor=etl_color, style='filled')
    
    g.node('extract', 'Extract\n\nFetch from arXiv API\n5 domains: AI, LG, CV, CL, ML', 
           fillcolor=etl_color)
    g.node('transform', 'Transform\n\nPydantic Validation\nSchema check\nDuplicate removal', 
           fillcolor=etl_color)
    g.node('load_etl', 'Load\n\nInsert to Cassandra\nBatch processing\nError handling', 
           fillcolor=etl_color)
    
    g.edge('arxiv', 'extract', label='Raw Data', fontsize='9')
    g.edge('extract', 'transform', label='500-1000', fontsize='9')
    g.edge('transform', 'load_etl', label='450-950 valid', fontsize='9')
    
    # ========== CASSANDRA DATABASE ==========
    g.node('cassandra', '📦 Cassandra Database\n\nTable: papers_raw\n18+ records\nValidated data', 
           fillcolor=cassandra_color, shape='cylinder')
    
    g.edge('load_etl', 'cassandra', label='Insert', fontsize='9', style='bold')
    
    # ========== PHASE 2: ELT (Databricks) ==========
    g.node('elt_label', 'PHASE 2: ELT\n(Databricks + Spark)', 
           shape='note', fillcolor=elt_color, style='filled')
    
    g.node('extract_elt', 'Extract\n\nRead Cassandra\nSpark Connector\nDirect query', 
           fillcolor=elt_color)
    g.node('load_bronze', 'Load (Bronze)\n\nRaw ingestion\nAdd metadata\n_ingestion_date\n_source_system', 
           fillcolor=elt_color)
    g.node('transform_silver', 'Transform (Silver)\n\nClean data\nRemove duplicates\nNormalize text\nExtract year', 
           fillcolor=elt_color)
    g.node('transform_gold', 'Transform (Gold)\n\nAggregations\nDimensions\nAnalytics tables\nML features', 
           fillcolor=elt_color)
    
    g.edge('cassandra', 'extract_elt', label='Read', fontsize='9', style='bold')
    g.edge('extract_elt', 'load_bronze', label='Bronze', fontsize='9')
    g.edge('load_bronze', 'transform_silver', label='Silver', fontsize='9')
    g.edge('transform_silver', 'transform_gold', label='Gold', fontsize='9')
    
    # ========== OUTPUTS ==========
    g.node('output_label', 'Outputs', 
           shape='note', fillcolor=output_color, style='filled')
    
    g.node('delta', '📊 Delta Tables\n\nQuery ready\nDashboard data\nOptimized format', 
           fillcolor=output_color)
    g.node('parquet', '📁 Parquet Export\n\nStandalone files\nDownstream tools\nPython, R, etc.', 
           fillcolor=output_color)
    g.node('ml', '🤖 ML Features\n\nEmbeddings (384-dim)\nTF-IDF vectors\nClustering ready', 
           fillcolor=output_color)
    
    g.edge('transform_gold', 'delta', fontsize='9')
    g.edge('transform_gold', 'parquet', fontsize='9')
    g.edge('transform_gold', 'ml', fontsize='9')
    
    # ========== STATISTICS ==========
    stats_text = '''
    ETL Stats:
    • Fetch: 500-1000 papers
    • Validate: 450-950 papers
    • Quality: 95%
    • Speed: ~30 sec/100 papers
    
    ELT Stats:
    • Bronze: 18+ rows (raw)
    • Silver: 18+ rows (clean)
    • Gold: 8+ tables (analytics)
    • Duration: ~45 min total
    '''
    
    g.node('stats', stats_text, shape='note', fillcolor='#f5f5f5', 
           fontname='monospace', fontsize='8')
    
    # Render
    output_dir = Path('docs')
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / 'architecture_diagram'
    
    g.render(str(output_path), cleanup=True, view=False)
    print(f"✅ Diagram generated: {output_path}.png")
    print(f"📊 Size: {output_path.with_suffix('.png').stat().st_size / 1024:.1f} KB")
    
    return output_path

if __name__ == '__main__':
    try:
        generate_architecture_diagram()
        print("\n✨ Architecture diagram created successfully!")
        print("📍 Location: docs/architecture_diagram.png")
        print("💡 Tip: Add to README.md with: ![Architecture](docs/architecture_diagram.png)")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n📦 Please install Graphviz:")
        print("   pip install graphviz")
        print("   Then download from: https://graphviz.org/download/")
