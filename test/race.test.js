const assert = require('assert');

// We simulate the server state and logic for testing
// In a real scenario, we might export logic from server.js
function calculateDistances(state, p1Rpm, p2Rpm, dt) {
    const p1SpeedMS = (p1Rpm / 60) * state.circumference;
    const p2SpeedMS = (p2Rpm / 60) * state.circumference;

    if (state.isRacing && !state.winner) {
        state.p1.dist += p1SpeedMS * dt;
        state.p2.dist += p2SpeedMS * dt;

        if (state.p1.dist >= state.targetDist) {
            state.p1.dist = state.targetDist;
            state.winner = 'Player 1';
            state.isRacing = false;
        } else if (state.p2.dist >= state.targetDist) {
            state.p2.dist = state.targetDist;
            state.winner = 'Player 2';
            state.isRacing = false;
        }
    }
    return state;
}

function testRaceLogic() {
    console.log('Running testRaceLogic...');
    
    let state = {
        isRacing: true,
        targetDist: 10, // short race
        circumference: 2.0,
        winner: null,
        p1: { dist: 0 },
        p2: { dist: 0 }
    };

    // P1 at 60 RPM = 1 rev/sec = 2m/s. In 3 seconds = 6m.
    state = calculateDistances(state, 60, 0, 3);
    assert.strictEqual(state.p1.dist, 6, 'P1 distance should be 6m');
    assert.strictEqual(state.winner, null, 'Race should still be ongoing');

    // Another 3 seconds = 12m total. Should win (at 10m).
    state = calculateDistances(state, 60, 0, 3);
    assert.strictEqual(state.p1.dist, 10, 'P1 distance should cap at targetDist');
    assert.strictEqual(state.winner, 'Player 1', 'P1 should be the winner');
    assert.strictEqual(state.isRacing, false, 'Race should be finished');

    console.log('✅ testRaceLogic passed');
}

function testConfigLogic() {
    console.log('Running testConfigLogic...');
    
    // Mocking the CONFIG command handling from server.js
    function handleConfig(state, cmd) {
        if (cmd.dist !== undefined) state.targetDist = parseFloat(cmd.dist) || 0;
        if (cmd.circ !== undefined) state.circumference = parseFloat(cmd.circ) || 0;
        return state;
    }

    let state = { targetDist: 500, circumference: 2.1 };
    
    // Test updating both
    state = handleConfig(state, { type: 'CONFIG', dist: 1000, circ: 2.2 });
    assert.strictEqual(state.targetDist, 1000);
    assert.strictEqual(state.circumference, 2.2);

    // Test zero value (the bug fix)
    state = handleConfig(state, { type: 'CONFIG', dist: 0 });
    assert.strictEqual(state.targetDist, 0, 'Should allow distance of 0');

    // Test partial update
    state = handleConfig(state, { type: 'CONFIG', circ: 1.5 });
    assert.strictEqual(state.targetDist, 0); // remains from previous call
    assert.strictEqual(state.circumference, 1.5);

    console.log('✅ testConfigLogic passed');
}

// Run all tests
try {
    testRaceLogic();
    testConfigLogic();
    console.log('\nAll tests passed successfully! 🚀');
} catch (error) {
    console.error('\n❌ Test failed!');
    console.error(error);
    process.exit(1);
}
