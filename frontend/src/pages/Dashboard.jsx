import React from 'react';

const Dashboard = ({ user }) => {
    // Тестовые данные игроков
    const players = [
        { id: 1, name: "Arman", pos: "Midfielder", dist: "1.2 km", speed: "22 km/h" },
        { id: 2, name: "Daniyar", pos: "Forward", dist: "0.8 km", speed: "25 km/h" }
    ];

    return (
        <div className="container">
            <header style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <h2>{user.role === 'admin' ? 'Admin Panel' : 'Scout Dashboard'}</h2>
                <span>Welcome, {user.username}</span>
            </header>

            <div className="card">
                <h3>Recent Players</h3>
                <table style={{width: '100%', borderCollapse: 'collapse'}}>
                    <thead>
                    <tr style={{textAlign: 'left', borderBottom: '2px solid #eee'}}>
                        <th style={{padding: '12px'}}>Name</th>
                        <th>Position</th>
                        <th>Total Distance</th>
                        <th>Top Speed</th>
                        <th>Action</th>
                    </tr>
                    </thead>
                    <tbody>
                    {players.map(p => (
                        <tr key={p.id} style={{borderBottom: '1px solid #eee'}}>
                            <td style={{padding: '12px'}}>{p.name}</td>
                            <td>{p.pos}</td>
                            <td>{p.dist}</td>
                            <td>{p.speed}</td>
                            <td><button style={{padding: '6px 12px', fontSize: '12px'}}>View Full Analysis</button></td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>

            {user.role === 'admin' && (
                <div className="card" style={{borderColor: '#ffc107'}}>
                    <h3>System Management</h3>
                    <button className="secondary">Manage Scouts</button>
                    <button className="secondary" style={{marginLeft: '10px'}}>View Server Logs</button>
                </div>
            )}
        </div>
    );
};

export default Dashboard;