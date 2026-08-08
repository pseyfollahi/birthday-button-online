self.addEventListener("push", function (event) {
    const data = event.data ? event.data.json() : {};

    const title = data.title || "پیام جدید";

    const options = {
        body: data.body || "🎉 تولدت مبارک 🎂",
        icon: "/static/icon.png",
        badge: "/static/icon.png"
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});