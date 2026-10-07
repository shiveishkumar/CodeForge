(() => {

    /* =====================================================
       THEME
    ===================================================== */

    const root =
        document.documentElement;

    const themeToggle =
        document.getElementById(
            "themeToggle"
        );


    if (themeToggle) {

        themeToggle.addEventListener(
            "click",
            () => {

                const current =
                    root.getAttribute(
                        "data-theme"
                    ) || "dark";


                const next =
                    current === "dark"
                        ? "light"
                        : "dark";


                root.setAttribute(
                    "data-theme",
                    next
                );


                localStorage.setItem(
                    "codeforge-theme",
                    next
                );

            }
        );

    }



    /* =====================================================
       COUNTERS
    ===================================================== */

    document
        .querySelectorAll(
            "[data-count]"
        )
        .forEach(counter => {

            const target =
                Number(
                    counter.dataset.count || 0
                );

            const start =
                performance.now();

            const duration =
                550;


            function animate(now) {

                const progress =
                    Math.min(
                        (now - start)
                        / duration,
                        1
                    );


                const eased =
                    1 -
                    Math.pow(
                        1 - progress,
                        3
                    );


                counter.textContent =
                    Math.round(
                        target * eased
                    );


                if (progress < 1) {

                    requestAnimationFrame(
                        animate
                    );

                }

            }


            requestAnimationFrame(
                animate
            );

        });



    /* =====================================================
       REAL AUDIT TIMELINE
    ===================================================== */

    const activityChart =
        document.getElementById(
            "activityChart"
        );


    const timelineItems =
        document.querySelectorAll(
            ".audit-timeline-item"
        );


    if (
        activityChart &&
        timelineItems.length > 0
    ) {

        const timeline = [];


        timelineItems.forEach(item => {

            timeline.push({
                label:
                    item.dataset.label,

                count:
                    Number(
                        item.dataset.count
                    )
            });

        });


        const width = 700;
        const height = 240;

        const padX = 28;
        const padY = 30;


        const maximum =
            Math.max(
                ...timeline.map(
                    point =>
                        point.count
                ),
                1
            );


        /* Horizontal grid */

        for (
            let i = 1;
            i <= 4;
            i++
        ) {

            const y =
                (height / 5) * i;


            activityChart.insertAdjacentHTML(
                "beforeend",
                `
                <line
                    class="chart-grid-line"
                    x1="0"
                    x2="${width}"
                    y1="${y}"
                    y2="${y}"
                />
                `
            );

        }


        const points =
            timeline.map(
                (point, index) => {

                    const x =
                        timeline.length === 1
                            ? width / 2
                            : padX +
                              (
                                  index /
                                  (
                                      timeline.length -
                                      1
                                  )
                              ) *
                              (
                                  width -
                                  padX * 2
                              );


                    const y =
                        height -
                        padY -
                        (
                            point.count /
                            maximum
                        ) *
                        (
                            height -
                            padY * 2
                        );


                    return {
                        x,
                        y,
                        label:
                            point.label,
                        count:
                            point.count
                    };

                }
            );


        const linePoints =
            points
                .map(
                    point =>
                        `${point.x},${point.y}`
                )
                .join(" ");


        if (points.length > 1) {

            const first =
                points[0];

            const last =
                points[
                    points.length - 1
                ];


            const areaPoints =
                `
                ${first.x},${height}
                ${linePoints}
                ${last.x},${height}
                `;


            activityChart.insertAdjacentHTML(
                "beforeend",
                `
                <defs>

                    <linearGradient
                        id="auditGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                    >

                        <stop
                            offset="0%"
                            stop-color="#4da3ff"
                            stop-opacity="0.50"
                        />

                        <stop
                            offset="100%"
                            stop-color="#4da3ff"
                            stop-opacity="0"
                        />

                    </linearGradient>

                </defs>


                <polygon
                    class="chart-area"
                    points="${areaPoints}"
                    fill="url(#auditGradient)"
                />


                <polyline
                    class="chart-line"
                    points="${linePoints}"
                />
                `
            );

        }


        points.forEach(point => {

            activityChart.insertAdjacentHTML(
                "beforeend",
                `
                <circle
                    class="chart-point"
                    cx="${point.x}"
                    cy="${point.y}"
                    r="5"
                >

                    <title>
                        ${point.label}
                        — ${point.count} event(s)
                    </title>

                </circle>
                `
            );

        });


        /* Replace Earlier / Latest labels */

        const chartLabels =
            document.querySelector(
                ".chart-labels"
            );


        if (
            chartLabels &&
            timeline.length > 0
        ) {

            chartLabels.innerHTML =
                `
                <span>
                    ${timeline[0].label}
                </span>

                <span>
                    ${
                        timeline[
                            timeline.length - 1
                        ].label
                    }
                </span>
                `;

        }

    }



    /* =====================================================
       REAL BUSINESS ACTIVITY DONUT
    ===================================================== */

    const donut =
        document.getElementById(
            "operationDonut"
        );

    const legend =
        document.getElementById(
            "operationLegend"
        );


    const operationItems =
        document.querySelectorAll(
            ".operation-data-item"
        );


    if (
        donut &&
        legend
    ) {

        const operations = [];


        operationItems.forEach(item => {

            operations.push({
                operation:
                    item.dataset.operation,

                count:
                    Number(
                        item.dataset.count || 0
                    )
            });

        });


        const total =
            operations.reduce(
                (sum, item) =>
                    sum + item.count,
                0
            );


        const colors = [
            "#4da3ff",
            "#bf7aff",
            "#ffad42",
            "#42d979",
            "#ff625c"
        ];


        if (
            total > 0 &&
            operations.length > 0
        ) {

            let angle = 0;

            const segments = [];


            operations.forEach(
                (item, index) => {

                    const percentage =
                        item.count /
                        total;


                    const endingAngle =
                        angle +
                        percentage *
                        360;


                    const color =
                        colors[
                            index %
                            colors.length
                        ];


                    segments.push(
                        `${color} ${angle}deg ${endingAngle}deg`
                    );


                    const percentageText =
                        Math.round(
                            percentage *
                            100
                        );


                    legend.insertAdjacentHTML(
                        "beforeend",
                        `
                        <div class="legend-row">

                            <div class="legend-name">

                                <span
                                    class="legend-dot"
                                    style="
                                        background:
                                        ${color}
                                    "
                                ></span>

                                ${
                                    formatActivityName(
                                        item.operation
                                    )
                                }

                            </div>


                            <div>

                                ${item.count}

                                <span
                                    style="
                                        opacity: 0.5;
                                        margin-left: 3px;
                                    "
                                >
                                    ${percentageText}%
                                </span>

                            </div>

                        </div>
                        `
                    );


                    angle =
                        endingAngle;

                }
            );


            donut.style.background =
                `conic-gradient(
                    ${segments.join(",")}
                )`;

        }

    }



    /* =====================================================
       FRIENDLY LABELS
    ===================================================== */

    function formatActivityName(name) {

        const names = {
            "DEPOSIT":
                "Deposits",

            "WITHDRAW":
                "Withdrawals",

            "TRANSFER":
                "Transfers",

            "INVENTORY":
                "Inventory Updates"
        };


        return names[name] || name;

    }


})();