import cmd

class Interface(cmd.Cmd):
    intro = "Bem-vindo ao console interativo! Digite 'ajuda' ou 'help' para ver os comandos.\n"
    prompt = ">>> "

    def do_devices(self, arg):
        print("Listing all devices connected to this network.")

    def do_talk(self, arg):
        name, message = map(str, arg.split())
        print(f"Sending message {message} to {name}.")

    def do_sendfile(self, arg):
        name, filename = map(str, arg.split())
        print(f"Sending file {filename} to {name}.")

    def do_sair(self, arg):
        print("Bye!")
        return True

    def do_EOF(self, arg):
        print("\nLeaving with Ctrl+D")
        return True

Interface().cmdloop()
