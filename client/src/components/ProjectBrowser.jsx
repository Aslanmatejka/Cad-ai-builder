import React, { useState, useEffect } from 'react';
import { getProjects, deleteProject } from '../api';
import './ProjectBrowser.css';

function ProjectBrowser({ onSelectProject, onClose, onNewProject }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('recent');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const data = await getProjects();
      setProjects(data.projects || []);
    } catch (error) {
      console.error('Failed to load projects:', error);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectClick = (project) => {
    onSelectProject(project);
    onClose();
  };

  const handleDeleteProject = async (e, projectId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this project and all its builds?')) return;
    try {
      await deleteProject(projectId);
      setProjects(prev => prev.filter(p => p.id !== projectId));
    } catch (error) {
      console.error('Failed to delete project:', error);
    }
  };

  const getFilteredAndSortedItems = () => {
    let items = [...projects];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      items = items.filter(item => {
        const searchText = (
          (item.name || '') +
          (item.last_prompt || '') +
          (item.description || '')
        ).toLowerCase();
        return searchText.includes(query);
      });
    }

    // Sort
    items.sort((a, b) => {
      if (sortBy === 'recent') {
        return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
      } else if (sortBy === 'oldest') {
        return new Date(a.created_at || 0) - new Date(b.created_at || 0);
      } else if (sortBy === 'name') {
        return (a.name || '').localeCompare(b.name || '');
      }
      return 0;
    });

    return items;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return date.toLocaleDateString();
  };

  const filteredItems = getFilteredAndSortedItems();

  return (
    <div className="project-browser-overlay">
      <div className="project-browser">
        <div className="browser-header">
          <div className="browser-title">
            <h2>Your Projects</h2>
            <button className="close-btn" onClick={onClose}>✕</button>
          </div>

          <div className="browser-controls">
            <div className="search-bar">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
              </svg>
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="filter-controls">
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest First</option>
                <option value="name">Name (A-Z)</option>
              </select>
            </div>
          </div>

          <button className="new-project-btn" onClick={onNewProject}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0a1 1 0 0 1 1 1v6h6a1 1 0 1 1 0 2H9v6a1 1 0 1 1-2 0V9H1a1 1 0 0 1 0-2h6V1a1 1 0 0 1 1-1z"/>
            </svg>
            New Project
          </button>
        </div>

        <div className="browser-content">
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading projects...</p>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <h3>No projects found</h3>
              <p>
                {searchQuery 
                  ? 'Try adjusting your search' 
                  : 'Start by creating your first project'}
              </p>
              <button className="cta-btn" onClick={onNewProject}>
                Create New Project
              </button>
            </div>
          ) : (
            <div className="projects-grid">
              {filteredItems.map((item) => (
                <div
                  key={item.id}
                  className="project-card product"
                  onClick={() => handleProjectClick(item)}
                >
                  <div className="card-preview">
                    <div className="preview-placeholder">
                      <svg width="48" height="48" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v8A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5v-8A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1h-3zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5z"/>
                      </svg>
                    </div>
                    <div className="card-type-badge">
                      📦 {item.build_count || 0} build{(item.build_count || 0) !== 1 ? 's' : ''}
                    </div>
                  </div>

                  <div className="card-content">
                    <h3 className="card-title">
                      {item.name || 'Untitled Project'}
                    </h3>
                    
                    {item.last_prompt && (
                      <p className="card-description">
                        {item.last_prompt.length > 80 
                          ? item.last_prompt.substring(0, 80) + '...' 
                          : item.last_prompt}
                      </p>
                    )}

                    <div className="card-footer">
                      <span className="card-date">{formatDate(item.updated_at)}</span>
                      <button 
                        className="delete-btn"
                        onClick={(e) => handleDeleteProject(e, item.id)}
                        title="Delete project"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="browser-stats">
          <span>{filteredItems.length} project{filteredItems.length !== 1 ? 's' : ''}</span>
        </div>
      </div>
    </div>
  );
}

export default ProjectBrowser;
